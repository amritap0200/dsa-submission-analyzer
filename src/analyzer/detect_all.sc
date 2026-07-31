import io.joern.dataflowengineoss.language.toExtendedCfgNode
import java.io.{File, FileWriter, BufferedWriter}
import java.util.regex.Pattern
import scala.io.Source

def toJsonValue(v: Any): String = v match {
  case s: String => "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"") + "\""
  case i: Int => i.toString
  case l: Long => l.toString
  case other => "\"" + other.toString.replace("\"", "\\\"") + "\""
}

def toJsonObject(m: Map[String, Any]): String =
  "{" + m.map { case (k, v) => "\"" + k + "\": " + toJsonValue(v) }.mkString(", ") + "}"

def detectNullDeref(): List[Map[String, Any]] = {
  val results = scala.collection.mutable.ListBuffer[Map[String, Any]]()
  val nullAssignments = cpg.assignment.where(_.source.isLiteral.code("(NULL|null|nullptr|0)"))
  val nullChecks = cpg.controlStructure.condition.ast.isCall.name("<operator>.(equals|notEquals)")

  cpg.call.name("<operator>.indirectFieldAccess|<operator>.indirection").foreach { deref =>
    deref.argument.headOption.foreach { t =>
      val reachesFromNull = t.reachableBy(nullAssignments.target).nonEmpty
      val guardedByCheck = t.reachableBy(nullChecks).nonEmpty
      if (reachesFromNull && !guardedByCheck) {
        results += Map(
          "error_type" -> "null_pointer_dereference",
          "line_number" -> deref.lineNumber.getOrElse(-1),
          "node_id" -> deref.id,
          "description" -> s"Pointer dereferenced at line ${deref.lineNumber.getOrElse(-1)} may be null."
        )
      }
    }
  }
  results.toList
}

def detectBufferOverflow(): List[Map[String, Any]] = {
  val results = scala.collection.mutable.ListBuffer[Map[String, Any]]()

  cpg.call.name("strcpy|strcat|gets|sprintf").foreach { call =>
    results += Map(
      "error_type" -> "buffer_overflow",
      "line_number" -> call.lineNumber.getOrElse(-1),
      "node_id" -> call.id,
      "description" -> s"Unsafe function '${call.name}' used at line ${call.lineNumber.getOrElse(-1)}."
    )
  }

  val boundsChecks = cpg.call.name("<operator>.(lessThan|greaterThan|lessEqualsThan|greaterEqualsThan)").argument

  cpg.call.name("<operator>.indirectIndexAccess").foreach { access =>
    access.argument.l.lift(1) match {
      case Some(idx: nodes.Identifier) =>
        if (idx.reachableBy(boundsChecks).isEmpty) {
          results += Map(
            "error_type" -> "buffer_overflow",
            "line_number" -> access.lineNumber.getOrElse(-1),
            "node_id" -> access.id,
            "description" -> s"Array access at line ${access.lineNumber.getOrElse(-1)} indexed by '${idx.name}' has no reachable bounds check."
          )
        }
      case _ =>
    }
  }
  results.toList
}

def detectMemoryManagement(): List[Map[String, Any]] = {
  val results = scala.collection.mutable.ListBuffer[Map[String, Any]]()
  case class Event(line: Int, kind: String, varName: String, nodeId: Long)

  cpg.method.foreach { method =>
    val allocEvents = method.ast.isCall.name("malloc|calloc|realloc").flatMap { call =>
      call.inAssignment.target.isIdentifier.name.headOption.map(v => Event(call.lineNumber.getOrElse(-1), "ALLOC", v, call.id))
    }.l
    val freeEvents = method.ast.isCall.name("free").flatMap { call =>
      call.argument.isIdentifier.name.headOption.map(v => Event(call.lineNumber.getOrElse(-1), "FREE", v, call.id))
    }.l

    (allocEvents ++ freeEvents).groupBy(_.varName).foreach { case (varName, events) =>
      val ordered = events.sortBy(_.line)
      var holding = false
      var lastAllocLine = -1
      ordered.foreach { ev =>
        if (ev.kind == "ALLOC") {
          if (holding) results += Map("error_type" -> "memory_leak", "line_number" -> lastAllocLine, "node_id" -> -1, "description" -> s"'$varName' overwritten before being freed.")
          holding = true; lastAllocLine = ev.line
        } else {
          if (!holding) results += Map("error_type" -> "double_free", "line_number" -> ev.line, "node_id" -> ev.nodeId, "description" -> s"'$varName' freed while not holding an active allocation.")
          else holding = false
        }
      }
      if (holding) results += Map("error_type" -> "memory_leak", "line_number" -> lastAllocLine, "node_id" -> -1, "description" -> s"'$varName' never freed.")
    }
  }
  results.toList
}

def updatesVariable(call: nodes.Call, varName: String): Boolean = {
  if (!call.name.matches(".*[Cc]rement|.*[Aa]ssignment.*")) return false
  val args = call.argument.l
  val lhs = args.headOption
  val rhs = args.lift(1)
  val lhsMatches = lhs.exists { case i: nodes.Identifier => i.name == varName; case _ => false }
  val isNoOp = rhs.exists { case r: nodes.Identifier => lhs.exists { case l: nodes.Identifier => l.name == r.name; case _ => false }; case _ => false }
  lhsMatches && !isNoOp
}

def detectInfiniteLoop(): List[Map[String, Any]] = {
  val results = scala.collection.mutable.ListBuffer[Map[String, Any]]()

  cpg.controlStructure.filter(_.controlStructureType == "FOR").foreach { loop =>
    val conditionVars = loop.condition.ast.isIdentifier.name.l.distinct
    val headerCalls = loop.astChildren.isCall.l
    val unmodified = conditionVars.filterNot(v => headerCalls.exists(c => updatesVariable(c, v)))
    if (conditionVars.nonEmpty && unmodified.nonEmpty) {
      results += Map("error_type" -> "infinite_loop_risk", "line_number" -> loop.lineNumber.getOrElse(-1), "node_id" -> loop.id, "description" -> s"For-loop: [${unmodified.mkString(", ")}] not updated in header.")
    }
  }

  cpg.controlStructure.filter(_.controlStructureType == "WHILE").foreach { loop =>
    val conditionVars = loop.condition.ast.isIdentifier.name.l.distinct
    val bodyCalls = loop.astChildren.isBlock.ast.isCall.l
    val unmodified = conditionVars.filterNot(v => bodyCalls.exists(c => updatesVariable(c, v)))
    if (conditionVars.nonEmpty && unmodified.size == conditionVars.size) {
      results += Map("error_type" -> "infinite_loop_risk", "line_number" -> loop.lineNumber.getOrElse(-1), "node_id" -> loop.id, "description" -> s"While-loop: [${unmodified.mkString(", ")}] never modified.")
    }
  }
  results.toList
}

def detectMissingReturn(): List[Map[String, Any]] = {
  val results = scala.collection.mutable.ListBuffer[Map[String, Any]]()
  cpg.method.filterNot(m => m.name == "<global>" || m.methodReturn.typeFullName == "void").foreach { method =>
    val exitPoints = method.cfgNode.filter(_.outE.isEmpty)
    if (exitPoints.filterNot(_.isReturn).nonEmpty) {
      results += Map("error_type" -> "missing_return", "line_number" -> method.lineNumber.getOrElse(-1), "node_id" -> method.id, "description" -> s"Method '${method.name}' may not return on all paths.")
    }
  }
  results.toList
}

// A variable counts as "written" if it's the direct target of a plain
// assignment, if its address is taken and passed into any call (covers
// scanf(&x, ...) and pass-by-reference into user functions), or if it's
// a parameter of the enclosing method (already provided by the caller).
def isDirectAssignmentTarget(ident: nodes.Identifier): Boolean = {
  ident.inCall.name(".*[Aa]ssignment.*").exists { call =>
    call.argument(1).headOption.exists {
      case i: nodes.Identifier => i.id == ident.id
      case _ => false
    }
  }
}

def isAddressOfTarget(ident: nodes.Identifier): Boolean = {
  ident.astParent.isCall.name("<operator>.addressOf").nonEmpty
}

def isParameterName(ident: nodes.Identifier): Boolean = {
  ident.method.parameter.name.toSet.contains(ident.name)
}

def isWrite(ident: nodes.Identifier): Boolean = {
  isDirectAssignmentTarget(ident) || isAddressOfTarget(ident) || isParameterName(ident)
}

def detectUninitialized(): List[Map[String, Any]] = {
  val results = scala.collection.mutable.ListBuffer[Map[String, Any]]()
  val allWrites = cpg.identifier.filter(isWrite)
  cpg.identifier.filterNot(isWrite).foreach { readIdent =>
    val safeName = Pattern.quote(readIdent.name)
    val priorWrites = allWrites.name(safeName)
    if (readIdent.reachableBy(priorWrites).isEmpty) {
      results += Map("error_type" -> "uninitialized_variable", "line_number" -> readIdent.lineNumber.getOrElse(-1), "node_id" -> readIdent.id, "description" -> s"'${readIdent.name}' read with no reachable prior write.")
    }
  }
  results.toList
}

def alreadyProcessed(outFile: File): Set[String] = {
  if (!outFile.exists()) return Set.empty
  val source = Source.fromFile(outFile)
  try {
    source.getLines().flatMap { line =>
      val idMatch = "\"student_id\":\\s*\"([^\"]+)\"".r.findFirstMatchIn(line)
      idMatch.map(_.group(1))
    }.toSet
  } finally {
    source.close()
  }
}

@main def exec(weekDir: String, isC: Boolean = true): Unit = {
  val startTime = System.currentTimeMillis()
  val studentDirs = new File(weekDir).listFiles().filter(_.isDirectory).sorted
  val outFile = new File(weekDir, "error_report.jsonl")

  val done = alreadyProcessed(outFile)
  if (done.nonEmpty) {
    println(s"Resuming: ${done.size} students already recorded in ${outFile.getPath}, skipping them")
  }

  val writer = new BufferedWriter(new FileWriter(outFile, true))

  studentDirs.zipWithIndex.foreach { case (dir, idx) =>
    if (done.contains(dir.getName)) {
      println(s"[${idx + 1}/${studentDirs.length}] ${dir.getName} already done, skipping")
    } else {
      val cpgFile = new File(dir, "cpg.bin")
      if (cpgFile.exists()) {
        try {
          val t0 = System.currentTimeMillis()
          importCpg(cpgFile.getAbsolutePath)

          val errors = scala.collection.mutable.ListBuffer[Map[String, Any]]()
          errors ++= detectNullDeref()
          errors ++= detectBufferOverflow()
          errors ++= detectInfiniteLoop()
          errors ++= detectMissingReturn()
          errors ++= detectUninitialized()
          if (isC) errors ++= detectMemoryManagement()

          val errorsJson = "[" + errors.map(toJsonObject).mkString(", ") + "]"
          val record = s"""{"student_id": "${dir.getName}", "file_path": "${cpgFile.getAbsolutePath}", "errors": $errorsJson}"""

          writer.write(record)
          writer.newLine()
          writer.flush()

          val elapsed = (System.currentTimeMillis() - t0) / 1000.0
          println(s"[${idx + 1}/${studentDirs.length}] ${dir.getName} done in ${elapsed}s")

          close
        } catch {
          case e: Exception =>
            println(s"[${idx + 1}/${studentDirs.length}] ${dir.getName} FAILED: ${e.getMessage}")
            val record = s"""{"student_id": "${dir.getName}", "file_path": "${cpgFile.getAbsolutePath}", "errors": [], "processing_error": "${e.getMessage.replace("\"", "'")}"}"""
            writer.write(record)
            writer.newLine()
            writer.flush()
        }
      } else {
        println(s"Skipping ${dir.getName}, no cpg.bin found")
      }
    }
  }

  writer.close()
  val totalTime = (System.currentTimeMillis() - startTime) / 1000.0
  println(s"\nDone. Output: ${outFile.getPath}")
  println(s"Total time this run: ${totalTime}s")
}
