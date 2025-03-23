"use client"

import type React from "react"

import { useState } from "react"
import {
  Clock,
  AlertTriangle,
  CheckCircle,
  FileText,
  MapIcon,
  Ruler,
  Timer,
  Pause,
  Download,
  MapPin,
  MessageSquare,
} from "lucide-react"
import MapboxMap from "@/components/mapbox-map"
import LocationInput from "@/components/location-input"
import ELDLogViewer from "@/components/eld-viewer"

const TRIP_API_ENDPOINT = process.env.NEXT_PUBLIC_TRIP_API_ENDPOINT

interface TripRequestBody {
  current_location: {
    name: string
    coordinates: [string, string]
  }
  pickup_location: {
    name: string
    coordinates: [string, string]
  }
  dropoff_location: {
    name: string
    coordinates: [string, string]
  }
  current_cycle_hours: number
}

interface Stop {
  coordinates: [number, number]
  timestamp: string | number
  duration: number
  stop_type: string
}

interface EldLog {
  date: string
  total_miles: number
  img_base64: string
  pdf_base64: string
}

interface TripResponse {
  id: string
  total_distance: number
  total_duration: number
  driving_duration: number
  stops: Stop[]
  eld_logs: EldLog[]
  hos: {
    warning: string
    hours_left_in_8_days: string
  }
}

export default function TripPlanner() {
  const [formData, setFormData] = useState({
    currentLocation: {
      text: "",
      coordinates: undefined as [number, number] | undefined,
      placeName: "",
    },
    pickupLocation: {
      text: "",
      coordinates: undefined as [number, number] | undefined,
      placeName: "",
    },
    dropoffLocation: {
      text: "",
      coordinates: undefined as [number, number] | undefined,
      placeName: "",
    },
    currentCycleUsed: "",
  })

  const [routeGenerated, setRouteGenerated] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [tripData, setTripData] = useState<TripResponse | null>(null)
  const [tripSummary, setTripSummary] = useState<string | null>(null)
  const [isLoadingSummary, setIsLoadingSummary] = useState(false)

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleLocationChange = (
    field: "currentLocation" | "pickupLocation" | "dropoffLocation",
    value: string,
    coordinates?: [number, number],
    placeName?: string,
  ) => {
    setFormData((prev) => ({
      ...prev,
      [field]: {
        text: value,
        coordinates,
        placeName: placeName || value,
      },
    }))
  }

  const handleGenerateRoute = async (e: React.FormEvent) => {
    e.preventDefault()
    setTripData(null)
    setRouteGenerated(false)
    setIsLoading(true)
    setTripSummary(null)

    if (
      !formData.currentLocation.coordinates ||
      !formData.pickupLocation.coordinates ||
      !formData.dropoffLocation.coordinates
    ) {
      alert("Please ensure all locations have valid coordinates")
      setIsLoading(false)
      return
    }

    const requestBody: TripRequestBody = {
      current_location: {
        name: formData.currentLocation.placeName,
        coordinates: [
          formData.currentLocation.coordinates[1].toString(),
          formData.currentLocation.coordinates[0].toString(),
        ],
      },
      pickup_location: {
        name: formData.pickupLocation.placeName,
        coordinates: [
          formData.pickupLocation.coordinates[1].toString(),
          formData.pickupLocation.coordinates[0].toString(),
        ],
      },
      dropoff_location: {
        name: formData.dropoffLocation.placeName,
        coordinates: [
          formData.dropoffLocation.coordinates[1].toString(),
          formData.dropoffLocation.coordinates[0].toString(),
        ],
      },
      current_cycle_hours: Number.parseFloat(formData.currentCycleUsed),
    }

    console.log("Sending data to API:", requestBody)

    try {
      const response = await fetch(TRIP_API_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        throw new Error(`API request failed with status ${response.status}`)
      }

      const data: TripResponse = await response.json()
      console.log("API Response:", data)

      setTripData(data)
      setRouteGenerated(true)
    } catch (error) {
      console.error("Error generating route:", error)
      alert("Failed to generate route. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  const handleGenerateSummary = async () => {
    console.log("Trip data:", tripData)

    if (!tripData || !tripData.id) {
      console.error("No trip data or trip ID available")
      setTripSummary("Unable to generate summary. Please refresh!")
      return
    }

    setIsLoadingSummary(true)

    try {
      const tripDataForLLM = {
        ...tripData,
        eld_logs: tripData.eld_logs.map((log) => ({
          ...log,
          img_base64: "",
          pdf_base64: "",
        })),
      }

      const response = await fetch("/api/proxy", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          tripId: tripData.id,
          data: tripDataForLLM,
        }),
      })

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`)
      }

      const data = await response.json()
      console.log("Summary response:", data)

      setTripSummary(data.summary || "No summary available.")
    } catch (error) {
      console.error("Error generating trip summary:", error)
      setTripSummary("Failed to generate trip summary. Please try again.")
    } finally {
      setIsLoadingSummary(false)
    }
  }

  const formatDuration = (hours: number) => {
    const totalMinutes = Math.round(hours * 60)
    const h = Math.floor(totalMinutes / 60)
    const m = totalMinutes % 60
    return `${h} ${h === 1 ? "hour" : "hours"} ${m} ${m === 1 ? "minute" : "minutes"}`
  }

  const formatDistance = (miles: number) => {
    return `${Math.round(miles)} miles`
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="container mx-auto">
          <h1 className="font-bold text-xl text-center">ELD Trip Planner</h1>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 max-w-6xl">
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-xl font-semibold mb-6">Trip Information</h2>
          <form onSubmit={handleGenerateRoute}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <LocationInput
                id="currentLocation"
                name="currentLocation"
                label="Current Location"
                value={formData.currentLocation.text}
                placeholder="Enter your current location"
                onChange={(value, coordinates, placeName) =>
                  handleLocationChange("currentLocation", value, coordinates, placeName)
                }
                required
              />
              <LocationInput
                id="pickupLocation"
                name="pickupLocation"
                label="Pickup Location"
                value={formData.pickupLocation.text}
                placeholder="Enter pickup location"
                onChange={(value, coordinates, placeName) =>
                  handleLocationChange("pickupLocation", value, coordinates, placeName)
                }
                required
              />
              <LocationInput
                id="dropoffLocation"
                name="dropoffLocation"
                label="Dropoff Location"
                value={formData.dropoffLocation.text}
                placeholder="Enter dropoff location"
                onChange={(value, coordinates, placeName) =>
                  handleLocationChange("dropoffLocation", value, coordinates, placeName)
                }
                required
              />
              <div>
                <label htmlFor="currentCycleUsed" className="block text-sm font-medium text-gray-700 mb-1">
                  Current Cycle Used (Hrs)
                </label>
                <div className="relative">
                  <input
                    type="text"
                    id="currentCycleUsed"
                    name="currentCycleUsed"
                    value={formData.currentCycleUsed}
                    onChange={handleInputChange}
                    placeholder="Enter hours used in cycle"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    required
                  />
                  <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none text-gray-400">
                    <Clock size={18} />
                  </div>
                </div>
              </div>
            </div>
            <div className="mt-6">
              <button
                type="submit"
                disabled={isLoading}
                className={`${
                  isLoading ? "bg-indigo-400" : "bg-indigo-600 hover:bg-indigo-700"
                } text-white px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center`}
              >
                {isLoading ? (
                  <>
                    <svg
                      className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Generating...
                  </>
                ) : (
                  "Generate Route"
                )}
              </button>
            </div>
          </form>
        </div>

        {routeGenerated && tripData && (
          <>
            {tripSummary ? (
              <div className="mb-6">
                <h2 className="text-xl font-semibold mb-4">Trip Summary</h2>
                <div className="bg-white rounded-lg shadow-sm p-6">
                  <div className="flex items-center mb-4 text-indigo-600">
                    <MessageSquare className="mr-2" size={20} />
                    <h3 className="font-medium text-lg">AI-Generated Summary</h3>
                  </div>
                  <div className="prose max-w-none">
                    <p className="text-gray-700 whitespace-pre-line">{tripSummary}</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="mb-6 flex justify-center">
                <button
                  onClick={handleGenerateSummary}
                  disabled={isLoadingSummary}
                  className={`${
                    isLoadingSummary ? "bg-indigo-400" : "bg-indigo-600 hover:bg-indigo-700"
                  } text-white px-6 py-3 rounded-md text-sm font-medium transition-colors flex items-center`}
                >
                  {isLoadingSummary ? (
                    <>
                      <svg
                        className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        ></circle>
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                      </svg>
                      Generating Trip Summary...
                    </>
                  ) : (
                    <>
                      <MessageSquare className="mr-2" size={16} />
                      Generate Trip Summary
                    </>
                  )}
                </button>
              </div>
            )}

            <div className="mb-6">
              <h2 className="text-xl font-semibold mb-4">Route Preview</h2>
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex items-center mb-4 text-indigo-600">
                  <MapIcon className="mr-2" size={20} />
                  <h3 className="font-medium text-lg">Route Map</h3>
                </div>
                <p className="text-gray-600 mb-4">
                  Interactive map showing your route with required stops and rest periods based on HOS regulations.
                </p>
                <p className="text-gray-600 mb-4 text-sm">
                  <strong>Map markers:</strong> Current: <MapPin className="text-green-500 inline-block" size={16} /> Pickup: <MapPin className="text-blue-500 inline-block" size={16} /> Fuel stop: <MapPin className="text-orange-500 inline-block" size={16} /> Rest stops: <MapPin className="text-yellow-500 inline-block" size={16} /> Dropoff: <MapPin className="text-purple-500 inline-block" size={16} />
                </p>
                <div className="h-[40vh] md:h-[50vh] w-full bg-gray-100 rounded-lg overflow-hidden mb-4">
                  <MapboxMap stops={tripData.stops} />
                </div>
              </div>
            </div>

            <div className="mb-6">
              <h2 className="text-xl font-semibold mb-4">Route Details</h2>
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="flex items-start">
                    <div className="bg-indigo-100 p-2 rounded-lg mr-4">
                      <Ruler className="text-indigo-600" size={20} />
                    </div>
                    <div>
                      <h3 className="font-medium">Total Distance</h3>
                      <p className="text-gray-600">{formatDistance(tripData.total_distance)}</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="bg-indigo-100 p-2 rounded-lg mr-4">
                      <Timer className="text-indigo-600" size={20} />
                    </div>
                    <div>
                      <h3 className="font-medium">Estimated Total Time</h3>
                      <p className="text-gray-600">{formatDuration(tripData.total_duration)}</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="bg-indigo-100 p-2 rounded-lg mr-4">
                      <Timer className="text-indigo-600" size={20} />
                    </div>
                    <div>
                      <h3 className="font-medium">Estimated Drive Time</h3>
                      <p className="text-gray-600">{formatDuration(tripData.driving_duration)}</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="bg-indigo-100 p-2 rounded-lg mr-4">
                      <Pause className="text-indigo-600" size={20} />
                    </div>
                    <div>
                      <h3 className="font-medium">Required Stops</h3>
                      <p className="text-gray-600">{tripData.stops.length - 2} stops</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="mb-6">
              <h2 className="text-xl font-semibold mb-4">Trip Stops</h2>
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th
                          scope="col"
                          className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                        >
                          Stop Type
                        </th>
                        <th
                          scope="col"
                          className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                        >
                          Time
                        </th>
                        <th
                          scope="col"
                          className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                        >
                          Duration
                        </th>
                        <th
                          scope="col"
                          className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                        >
                          Coordinates
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {tripData.stops.map((stop, index) => (
                        <tr key={index}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 capitalize">
                            {stop.stop_type}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {stop.timestamp === 0
                              ? "Start"
                              : typeof stop.timestamp === "string"
                                ? new Date(stop.timestamp).toLocaleString()
                                : "N/A"}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {stop.duration > 0 ? `${stop.duration} hours` : "N/A"}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {`${stop.coordinates[1].toFixed(6)}, ${stop.coordinates[0].toFixed(6)}`}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <div className="mb-6">
              <h2 className="text-xl font-semibold mb-4">ELD Logs Preview</h2>
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex items-center mb-4 text-indigo-600">
                  <FileText className="mr-2" size={20} />
                  <h3 className="font-medium text-lg">Daily Log Sheets</h3>
                </div>
                <p className="text-gray-600 mb-4">
                  Preview of your automatically generated ELD logs based on the planned route and current hours.
                </p>

                {tripData.eld_logs.length > 0 ? (
                  <>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-4">
                      {tripData.eld_logs.map((log, index) => (
                        <div
                          key={index}
                          className="h-[500px] bg-gray-50 rounded-lg overflow-hidden border border-gray-200"
                        >
                          <ELDLogViewer
                            imgBase64Data={log.img_base64}
                            pdfBase64Data={log.pdf_base64}
                            dayNumber={index + 1}
                            date={log.date}
                          />
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="flex justify-center items-center h-64 bg-gray-50 rounded-lg">
                    <p className="text-gray-500">No log sheets available</p>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
