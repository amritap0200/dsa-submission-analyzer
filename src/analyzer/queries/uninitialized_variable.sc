import io.joern.dataflowengineoss.language.toExtendedCfgNode

@main def exec(cpgPath: String) = {
  importCpg(cpgPath)
  val results = scala.collection.mutable.ListBuffer[Map[String, Any]]()

  def isWrite(ident: nodes.Identifier): Boolean = {
    ident.inCall.name(".*[Aa]ssignment.*").exists { call =>
      call.argument.l.headOption.exists {
        case i: nodes.Identifier => i.id == ident.id
        case _ => false
      }
    }
  }

  val allWrites = cpg.identifier.filter(isWrite)

  cpg.identifier.filterNot(isWrite).foreach { readIdent =>
    val varName = readIdent.name
    val priorWrites = allWrites.name(varName)
    val reaches = readIdent.reachableBy(priorWrites).nonEmpty

    if (!reaches) {
      results += Map(
        "error_type" -> "uninitialized_variable",
        "line_number" -> readIdent.lineNumber.getOrElse(-1),
        "node_id" -> readIdent.id,
        "description" -> s"Variable '$varName' read at line ${readIdent.lineNumber.getOrElse(-1)} has no reachable prior write."
      )
    }
  }

  println(results.toList)
}
