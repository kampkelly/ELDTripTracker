"use client"

import { useEffect, useRef } from "react"

export default function EldLogSheet() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    // Set canvas dimensions
    canvas.width = canvas.offsetWidth
    canvas.height = canvas.offsetHeight

    // Draw the ELD log grid
    drawEldLogGrid(ctx, canvas.width, canvas.height)

    // Draw the driver's status line
    drawDriverStatusLine(ctx, canvas.width, canvas.height)

    // Handle window resize
    const handleResize = () => {
      if (!canvas || !ctx) return

      canvas.width = canvas.offsetWidth
      canvas.height = canvas.offsetHeight

      drawEldLogGrid(ctx, canvas.width, canvas.height)
      drawDriverStatusLine(ctx, canvas.width, canvas.height)
    }

    window.addEventListener("resize", handleResize)

    return () => {
      window.removeEventListener("resize", handleResize)
    }
  }, [])

  // Function to draw the ELD log grid
  const drawEldLogGrid = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
    ctx.clearRect(0, 0, width, height)

    // Background
    ctx.fillStyle = "#f9fafb"
    ctx.fillRect(0, 0, width, height)

    // Grid settings
    const hourWidth = width / 24
    const statusHeight = height / 5

    // Draw vertical hour lines
    ctx.strokeStyle = "#d1d5db"
    ctx.lineWidth = 1

    for (let hour = 0; hour <= 24; hour++) {
      const x = hour * hourWidth
      ctx.beginPath()
      ctx.moveTo(x, 0)
      ctx.lineTo(x, height - 40)
      ctx.stroke()

      // Hour labels
      if (hour < 24) {
        ctx.fillStyle = "#6b7280"
        ctx.font = "10px Arial"
        ctx.textAlign = "center"
        ctx.fillText(`${hour}:00`, x + hourWidth / 2, height - 25)
      }
    }

    // Draw horizontal status lines
    const statuses = ["OFF", "SB", "D", "ON"]

    for (let i = 0; i <= statuses.length; i++) {
      const y = i * statusHeight
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(width, y)
      ctx.stroke()

      if (i < statuses.length) {
        ctx.fillStyle = "#6b7280"
        ctx.font = "12px Arial"
        ctx.textAlign = "left"
        ctx.fillText(statuses[i], 5, y + statusHeight / 2 + 5)
      }
    }

    // Title
    ctx.fillStyle = "#111827"
    ctx.font = "bold 14px Arial"
    ctx.textAlign = "center"
    ctx.fillText("Driver's Daily Log", width / 2, height - 5)
  }

  // Function to draw the driver's status line
  const drawDriverStatusLine = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
    const hourWidth = width / 24
    const statusHeight = height / 5

    // Example driver status data (in a real app, this would come from your backend)
    const driverStatus = [
      { status: "OFF", startHour: 0, endHour: 6 },
      { status: "ON", startHour: 6, endHour: 7 },
      { status: "D", startHour: 7, endHour: 11 },
      { status: "SB", startHour: 11, endHour: 11.5 },
      { status: "D", startHour: 11.5, endHour: 15 },
      { status: "ON", startHour: 15, endHour: 16 },
      { status: "OFF", startHour: 16, endHour: 24 },
    ]

    // Draw status lines
    ctx.lineWidth = 3

    driverStatus.forEach((period) => {
      const startX = period.startHour * hourWidth
      const endX = period.endHour * hourWidth
      let y

      switch (period.status) {
        case "OFF":
          y = statusHeight * 0.5
          ctx.strokeStyle = "#4F46E5" // Indigo
          break
        case "SB":
          y = statusHeight * 1.5
          ctx.strokeStyle = "#F59E0B" // Amber
          break
        case "D":
          y = statusHeight * 2.5
          ctx.strokeStyle = "#10B981" // Emerald
          break
        case "ON":
          y = statusHeight * 3.5
          ctx.strokeStyle = "#EF4444" // Red
          break
        default:
          y = 0
      }

      ctx.beginPath()
      ctx.moveTo(startX, y)
      ctx.lineTo(endX, y)
      ctx.stroke()

      // Draw vertical lines connecting status changes
      if (period !== driverStatus[0]) {
        const prevPeriod = driverStatus[driverStatus.indexOf(period) - 1]
        let prevY

        switch (prevPeriod.status) {
          case "OFF":
            prevY = statusHeight * 0.5
            break
          case "SB":
            prevY = statusHeight * 1.5
            break
          case "D":
            prevY = statusHeight * 2.5
            break
          case "ON":
            prevY = statusHeight * 3.5
            break
          default:
            prevY = 0
        }

        ctx.beginPath()
        ctx.moveTo(startX, prevY)
        ctx.lineTo(startX, y)
        ctx.stroke()
      }
    })
  }

  return (
    <div className="w-full h-full bg-white p-4">
      <canvas ref={canvasRef} className="w-full h-full" />
    </div>
  )
}

