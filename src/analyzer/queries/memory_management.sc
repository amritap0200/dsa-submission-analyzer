@main def exec(cpgPath: String) = {
  importCpg(cpgPath)
  val results = scala.collection.mutable.ListBuffer[Map[String, Any]]()

  case class Event(line: Int, kind: String, varName: String, nodeId: Long)

  cpg.method.foreach { method =>
    val allocEvents = method.ast.isCall.name("malloc|calloc|realloc").flatMap { call =>
      call.inAssignment.target.isIdentifier.name.headOption.map { v =>
        Event(call.lineNumber.getOrElse(-1), "ALLOC", v, call.id)
      }
    }.l

    val freeEvents = method.ast.isCall.name("free").flatMap { call =>
      call.argument.isIdentifier.name.headOption.map { v =>
        Event(call.lineNumber.getOrElse(-1), "FREE", v, call.id)
      }
    }.l

    val byVariable = (allocEvents ++ freeEvents).groupBy(_.varName)

    byVariable.foreach { case (varName, events) =>
      val ordered = events.sortBy(_.line)
      var holdingMemory = false
      var lastAllocLine = -1

      ordered.foreach { ev =>
        if (ev.kind == "ALLOC") {
          if (holdingMemory) {
            results += Map(
              "error_type" -> "memory_leak",
              "line_number" -> lastAllocLine,
              "node_id" -> -1,
              "description" -> s"'$varName' allocated at line $lastAllocLine is overwritten by a new allocation at line ${ev.line} before being freed."
            )
          }
          holdingMemory = true
          lastAllocLine = ev.line
        } else { // FREE
          if (!holdingMemory) {
            results += Map(
              "error_type" -> "double_free",
              "line_number" -> ev.line,
              "node_id" -> ev.nodeId,
              "description" -> s"'$varName' freed at line ${ev.line} while not currently holding an active allocation."
            )
          } else {
            holdingMemory = false
          }
        }
      }

      if (holdingMemory) {
        results += Map(
          "error_type" -> "memory_leak",
          "line_number" -> lastAllocLine,
          "node_id" -> -1,
          "description" -> s"'$varName' allocated at line $lastAllocLine is never freed in this function."
        )
      }
    }
  }

  println(results.toList)
}
