import io.joern.dataflowengineoss.language.toExtendedCfgNode

@main def exec(cpgPath: String) = {
  importCpg(cpgPath)
  val results = scala.collection.mutable.ListBuffer[Map[String, Any]]()

  // Find pointer/reference variables assigned null, then check for
  // a dereference reachable from that assignment without an intervening null check
  val nullAssignments = cpg.assignment
    .where(_.source.isLiteral.code("(NULL|null|nullptr|0)"))

  val nullChecks = cpg.controlStructure.condition
    .ast.isCall.name("<operator>.(equals|notEquals)")

  cpg.call.name("<operator>.indirectFieldAccess|<operator>.indirection").foreach { deref =>
    val target = deref.argument.headOption
    target.foreach { t =>
      val reachesFromNull = t.reachableBy(nullAssignments.target).nonEmpty
      val guardedByCheck = t.reachableBy(nullChecks).nonEmpty
      if (reachesFromNull && !guardedByCheck) {
        results += Map(
          "error_type" -> "null_pointer_dereference",
          "line_number" -> deref.lineNumber.getOrElse(-1),
          "node_id" -> deref.id,
          "description" -> s"Pointer dereferenced at line ${deref.lineNumber.getOrElse(-1)} may be null; no guarding check found upstream."
        )
      }
    }
  }

  println(results.toList)
}
