import { type NextRequest, NextResponse } from "next/server"

// The base URL of the external API
const API_BASE_URL = process.env.NEXT_PUBLIC_TRIP_API_ENDPOINT


export async function POST(request: NextRequest) {
  try {
    // Get the trip ID and data from the request
    const { tripId, data } = await request.json()

    if (!tripId) {
      return NextResponse.json({ error: "Trip ID is required" }, { status: 400 })
    }

    // Construct the URL for the external API
    const apiUrl = `${API_BASE_URL}/${tripId}`

    console.log('>>>>apiURL', apiUrl)

    // Forward the request to the external API
    const response = await fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    })

    // Check if the request was successful
    if (!response.ok) {
      const errorText = await response.text()
      console.error(`API request failed with status ${response.status}: ${errorText}`)
      return NextResponse.json(
        { error: `API request failed with status ${response.status}` },
        { status: response.status },
      )
    }

    // Return the response from the external API
    const responseData = await response.json()
    return NextResponse.json(responseData)
  } catch (error) {
    console.error("Error in proxy API route:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

