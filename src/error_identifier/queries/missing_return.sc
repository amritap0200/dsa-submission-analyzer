@main def exec(cpgPath: String) = {
  importCpg(cpgPath)
  val results = scala.collection.mutable.ListBuffer[Map[String, Any]]()

  cpg.method.filterNot(m => m.name == "<global>" || m.methodReturn.typeFullName == "void").foreach { method =>
    val exitPoints = method.cfgNode.filter(_.outE.isEmpty)
    val exitPointsWithoutReturn = exitPoints.filterNot(_.isReturn)

    if (exitPointsWithoutReturn.nonEmpty) {
      results += Map(
        "error_type" -> "missing_return",
        "line_number" -> method.lineNumber.getOrElse(-1),
        "node_id" -> method.id,
        "description" -> s"Method '${method.name}' has a non-void return type but at least one path does not reach a return statement."
      )
    }
  }

  println(results.toList)
}
