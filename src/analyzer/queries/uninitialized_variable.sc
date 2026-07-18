import io.joern.dataflowengineoss.language.toExtendedCfgNode

@main def exec(cpgPath: String) = {
  importCpg(cpgPath)
  val results = scala.collection.mutable.ListBuffer[Map[String, Any]]()

  cpg.identifier.foreach { ident =>
    val varName = ident.name
    val assignmentsToVar = cpg.assignment
      .where(_.target.isIdentifier.name(varName))
      .argument

    val reaches = ident.reachableBy(assignmentsToVar).nonEmpty
    val isDeclaration = ident.inAssignment.target.isIdentifier.name(varName).nonEmpty

    if (!reaches && !isDeclaration) {
      results += Map(
        "error_type" -> "uninitialized_variable",
        "line_number" -> ident.lineNumber.getOrElse(-1),
        "node_id" -> ident.id,
        "description" -> s"Variable '$varName' used at line ${ident.lineNumber.getOrElse(-1)} with no reachable prior assignment."
      )
    }
  }

  println(results.toList)
}
