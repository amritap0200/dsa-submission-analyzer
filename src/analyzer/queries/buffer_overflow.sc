import io.joern.dataflowengineoss.language.toExtendedCfgNode

@main def exec(cpgPath: String) = {
  importCpg(cpgPath)
  val results = scala.collection.mutable.ListBuffer[Map[String, Any]]()

  // unsafe string function usage, applies mainly to C/C++
  cpg.call.name("strcpy|strcat|gets|sprintf").foreach { call =>
    results += Map(
      "error_type" -> "buffer_overflow",
      "line_number" -> call.lineNumber.getOrElse(-1),
      "node_id" -> call.id,
      "description" -> s"Unsafe function '${call.name}' used at line ${call.lineNumber.getOrElse(-1)}; no bounds enforced by this function."
    )
  }

  // unguarded array index access, language-agnostic
  val boundsChecks = cpg.call.name("<operator>.(lessThan|greaterThan|lessEqualsThan|greaterEqualsThan)").argument

  cpg.call.name("<operator>.indexAccess").foreach { access =>
    val indexArg = access.argument.l.lift(1)
    indexArg.foreach { idx =>
      val guarded = idx.reachableBy(boundsChecks).nonEmpty
      if (!guarded) {
        results += Map(
          "error_type" -> "buffer_overflow",
          "line_number" -> access.lineNumber.getOrElse(-1),
          "node_id" -> access.id,
          "description" -> s"Array access at line ${access.lineNumber.getOrElse(-1)} has no reachable bounds check on its index."
        )
      }
    }
  }

  println(results.toList)
}
