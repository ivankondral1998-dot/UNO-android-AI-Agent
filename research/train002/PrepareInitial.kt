package org.unovyra.uno.research

import java.nio.file.*

fun main(args:Array<String>) {
    require(args.size==1)
    val root=Paths.get(args[0]);Files.createDirectories(root)
    for(seed in listOf(260015L,260016L,260017L)) {
        val model=Ladder.model(seed);val values=model.values()
        Files.newBufferedWriter(root.resolve("initial-$seed.tsv"),StandardOpenOption.CREATE_NEW).use {o ->
            for(r in model.rules) o.appendLine(listOf(r.name,r.rows,r.cols,r.cap,r.box,values.getValue(r.name).joinToString(",")).joinToString("\t"))
        }
        println("KOTLIN_INITIAL seed=$seed weights=${model.fingerprint()} schema=${model.schemaHash()}")
    }
}
