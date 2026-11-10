// pdf_extract.swift - print a PDF's text as macOS PDFKit extracts it (what Preview's copy/export uses).
// Usage: swift tools/pdf_extract.swift <file.pdf>
import Foundation
import PDFKit

guard CommandLine.arguments.count == 2,
      let doc = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1])) else {
    FileHandle.standardError.write("usage: swift pdf_extract.swift <file.pdf> (file must be a readable PDF)\n".data(using: .utf8)!)
    exit(1)
}
print(doc.string ?? "", terminator: "")
