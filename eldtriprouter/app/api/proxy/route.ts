import { type NextRequest, NextResponse } from "next/server"

const API_BASE_URL = process.env.NEXT_PUBLIC_TRIP_API_ENDPOINT


export async function POST(request: NextRequest) {
  try {
    const { tripId, data } = await request.json()

    if (!tripId) {
      return NextResponse.json({ error: "Trip ID is required" }, { status: 400 })
    }

    const apiUrl = `${API_BASE_URL}/${tripId}`

    const response = await fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error(`API request failed with status ${response.status}: ${errorText}`)
      return NextResponse.json(
        { error: `API request failed with status ${response.status}` },
        { status: response.status },
      )
    }

    const responseData = await response.json()
    return NextResponse.json(responseData)
  } catch (error) {
    console.error("Error in proxy API route:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
