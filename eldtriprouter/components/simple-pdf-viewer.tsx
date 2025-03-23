"use client"
import { Download, FileText } from "lucide-react"

interface SimplePDFViewerProps {
  imgBase64Data: string // base64 encoded PDF
  pdfBase64Data: string // base64 encoded PDF
  dayNumber?: number
  date?: string
}

export default function SimplePDFViewer({ imgBase64Data, pdfBase64Data, dayNumber, date }: SimplePDFViewerProps) {
  // Function to download the PDF
  const handleDownload = () => {
    if (!pdfBase64Data) return

    const pdfUrl = `data:application/pdf;base64,${pdfBase64Data}`
    const link = document.createElement("a")
    link.href = pdfUrl
    link.download = date ? `ELD_Log_${date}.pdf` : `ELD_Log_Day_${dayNumber || 1}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  if (!pdfBase64Data) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-4">
        <FileText size={48} className="text-indigo-400 mb-4" />
        <h3 className="font-medium text-lg mb-2">{date ? `Log for ${date}` : `Day ${dayNumber || 1} Log`}</h3>
        <p className="text-gray-500 text-center mb-4">PDF data not available for this log.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex justify-between items-center mb-2">
        <h3 className="font-medium">{date ? `Log for ${date}` : `Day ${dayNumber || 1} Log`}</h3>
        <button onClick={handleDownload} className="flex items-center text-indigo-600 hover:text-indigo-800">
          <Download size={16} className="mr-1" />
          Download
        </button>
      </div>
      <div className="relative flex-1 bg-white border border-gray-200 rounded-md overflow-hidden">
      <img
        src={`data:image/png;base64,${imgBase64Data}`}
        alt={date ? `ELD Log ${date}` : `ELD Log Day ${dayNumber || 1}`}
        className="w-full h-full"
      />
      </div>
    </div>
  )
}

