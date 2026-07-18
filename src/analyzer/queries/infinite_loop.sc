@main def exec(cpgPath: String) = {
  importCpg(cpgPath)
  val results = scala.collection.mutable.ListBuffer[Map[String, Any]]()

  cpg.controlStructure.filter(cs => cs.controlStructureType == "WHILE" || cs.controlStructureType == "FOR").foreach { loop =>
    val conditionVars = loop.condition.ast.isIdentifier.name.l.distinct
    val bodyAssignments = loop.astChildren.isBlock.ast.isIdentifier
      .where(_.inAssignment)
      .name.l

    val unmodified = conditionVars.filterNot(bodyAssignments.contains)

    if (conditionVars.nonEmpty && unmodified.size == conditionVars.size) {
      results += Map(
        "error_type" -> "infinite_loop_risk",
        "line_number" -> loop.lineNumber.getOrElse(-1),
        "node_id" -> loop.id,
        "description" -> s"Loop at line ${loop.lineNumber.getOrElse(-1)} has condition variable(s) [${conditionVars.mkString(", ")}] never modified in its body."
      )
    }
  }

  println(results.toList)
}
