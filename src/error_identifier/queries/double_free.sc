@main def exec(cpgPath: String) = {
  importCpg(cpgPath)
  val results = scala.collection.mutable.ListBuffer[Map[String, Any]]()

  cpg.method.foreach { method =>
    val freeCalls = method.ast.isCall.name("free").l
    val freedVarCounts = freeCalls
      .flatMap(_.argument.isIdentifier.name.l)
      .groupBy(identity)
      .view.mapValues(_.size)

    freedVarCounts.filter(_._2 > 1).foreach { case (varName, count) =>
      val lines = freeCalls.filter(_.argument.isIdentifier.name(varName).nonEmpty).flatMap(_.lineNumber)
      results += Map(
        "error_type" -> "double_free",
        "line_number" -> lines.headOption.getOrElse(-1),
        "node_id" -> -1,
        "description" -> s"Variable '$varName' passed to free() $count times in the same function."
      )
    }
  }

  println(results.toList)
}
