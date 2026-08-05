@main def exec(cpgPath: String) = {
  importCpg(cpgPath)
  val results = scala.collection.mutable.ListBuffer[Map[String, Any]]()

  cpg.method.foreach { method =>
    val mallocCalls = method.ast.isCall.name("malloc|calloc|realloc")
    val freeCalls = method.ast.isCall.name("free")
    val freedVars = freeCalls.argument.isIdentifier.name.toSet

    mallocCalls.foreach { m =>
      val assignedVar = m.inAssignment.target.isIdentifier.name.headOption
      assignedVar.foreach { v =>
        if (!freedVars.contains(v)) {
          results += Map(
            "error_type" -> "memory_leak",
            "line_number" -> m.lineNumber.getOrElse(-1),
            "node_id" -> m.id,
            "description" -> s"Allocation for '$v' at line ${m.lineNumber.getOrElse(-1)} has no matching free() call in this function."
          )
        }
      }
    }
  }

  println(results.toList)
}
