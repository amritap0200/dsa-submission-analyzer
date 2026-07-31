@main def exec(cpgPath: String) = {
  importCpg(cpgPath)
  val results = scala.collection.mutable.ListBuffer[Map[String, Any]]()

  def updatesVariable(call: nodes.Call, varName: String): Boolean = {
    val isUpdateOp = call.name.matches(".*[Cc]rement|.*[Aa]ssignment.*")
    if (!isUpdateOp) return false

    val args = call.argument.l
    val lhs = args.headOption
    val rhs = args.lift(1)

    val lhsMatches = lhs.exists {
      case i: nodes.Identifier => i.name == varName
      case _ => false
    }
    // for augmented assignment, guard against i = i doing nothing useful
    val isNoOp = rhs.exists {
      case r: nodes.Identifier => rhs.isDefined && lhs.exists {
        case l: nodes.Identifier => l.name == r.name
        case _ => false
      }
      case _ => false
    }

    lhsMatches && !isNoOp
  }

  // FOR loops: check header children, not body
  cpg.controlStructure.filter(_.controlStructureType == "FOR").foreach { loop =>
    val conditionVars = loop.condition.ast.isIdentifier.name.l.distinct
    val headerCalls = loop.astChildren.isCall.l

    val unmodified = conditionVars.filterNot(v => headerCalls.exists(c => updatesVariable(c, v)))

    if (conditionVars.nonEmpty && unmodified.nonEmpty) {
      results += Map(
        "error_type" -> "infinite_loop_risk",
        "line_number" -> loop.lineNumber.getOrElse(-1),
        "node_id" -> loop.id,
        "description" -> s"For-loop at line ${loop.lineNumber.getOrElse(-1)}: [${unmodified.mkString(", ")}] not updated in the loop header."
      )
    }
  }

  // WHILE loops: body-based check still applies, since while has no header update slot
  cpg.controlStructure.filter(_.controlStructureType == "WHILE").foreach { loop =>
    val conditionVars = loop.condition.ast.isIdentifier.name.l.distinct
    val bodyCalls = loop.astChildren.isBlock.ast.isCall.l

    val unmodified = conditionVars.filterNot(v => bodyCalls.exists(c => updatesVariable(c, v)))

    if (conditionVars.nonEmpty && unmodified.size == conditionVars.size) {
      results += Map(
        "error_type" -> "infinite_loop_risk",
        "line_number" -> loop.lineNumber.getOrElse(-1),
        "node_id" -> loop.id,
        "description" -> s"While-loop at line ${loop.lineNumber.getOrElse(-1)}: [${unmodified.mkString(", ")}] never modified in body."
      )
    }
  }

  println(results.toList)
}
