"use client"

import { useEffect, useRef } from "react"
import mapboxgl from "mapbox-gl"
import "mapbox-gl/dist/mapbox-gl.css"
// import MapboxDirections from "@mapbox/mapbox-gl-directions/dist/mapbox-gl-directions.css"
// import "@mapbox/mapbox-gl-directions/dist/mapbox-gl-directions.css"

import MapboxDirections from "@mapbox/mapbox-gl-directions/dist/mapbox-gl-directions"
import "@mapbox/mapbox-gl-directions/dist/mapbox-gl-directions.css"


// Note: In a real application, you would use an environment variable for the token
// This is just a placeholder and would be replaced with your actual Mapbox token
const MAPBOX_TOKEN = "pk.eyJ1Ijoia2FtcGtlbGx5IiwiYSI6ImNtOGZvbmU3MDBlcDgybHB3YTRlMThyMXkifQ.rPz58hWmBPYkKtvN5uw9mA"

interface Stop {
  coordinates: [number, number]
  timestamp: string | number
  duration: number
  stop_type: string
}

type MapboxMapProps = {
  stops?: Stop[]
  currentLocation?: [number, number]
  pickupLocation?: [number, number]
  dropoffLocation?: [number, number]
}

// Function to get marker color based on stop type
const getMarkerColor = (stopType: string): string => {
  switch (stopType.toLowerCase()) {
    case "current location":
      return "#4F46E5" // Indigo
    case "pickup":
      return "#F59E0B" // Amber
    case "dropoff":
      return "#EF4444" // Red
    case "rest break":
      return "#10B981" // Emerald
    case "fuel":
      return "#8B5CF6" // Purple
    default:
      return "#6B7280" // Gray
  }
}

export default function MapboxMap({
  stops = [],
  currentLocation = [-87.63924407958984, 41.87867736816406], // Default: Chicago
  pickupLocation = [-83.74621216, 32.26003672], // Default: Macon, GA
  dropoffLocation = [-80.19515228271484, 25.774606704711914], // Default: Miami
}: MapboxMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<mapboxgl.Map | null>(null)

  useEffect(() => {
    if (!mapContainer.current) return

    // Initialize the map
    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: "mapbox://styles/mapbox/streets-v12",
      center: [-95.7129, 37.0902], // Center of US
      zoom: 3,
      accessToken: MAPBOX_TOKEN,
    })

    const directions = new MapboxDirections({
      accessToken: MAPBOX_TOKEN,
      profile: "mapbox/driving",
      alternatives: false,
      unit: "metric",
      interactive: false, // This disables the interactive placement of waypoints via clicks
      instructions: {
        showWaypointInstructions: true,
      },
      controls: {
        inputs: true,
        instructions: true,
        profileSwitcher: false,
      },
    })

    // Add navigation controls
    map.current.addControl(new mapboxgl.NavigationControl(), "top-right")
    map.current.addControl(directions, "top-left")
    map.current.setConfigProperty("basemap", "show3dObjects", true)
    map.current.setConfigProperty("basemap", "colorTrunks", "red")

    // Example route - in a real app, this would come from your backend
    /*const route = {
      type: "Feature",
      properties: {},
      geometry: {
        type: "LineString",
        coordinates: [
          [-87.63924407958984,41.87867736816406], // San Francisco
          [-83.74621216,32.26003672], // Las Vegas
          [-80.19515228271484,25.774606704711914], // Los Angeles
          // [-112.074, 33.4484], // Phoenix
        ],
      },
    }*/

    // Add route when map loads
    map.current.on("load", () => {
      if (!map.current) return

      if (stops && stops.length > 0) {
        // Use stops from API response
        const bounds = new mapboxgl.LngLatBounds()

        // Add markers for each stop
        stops.forEach((stop, index) => {
          const [lng, lat] = stop.coordinates
          const color = getMarkerColor(stop.stop_type)

          // Create popup content
          let popupContent = `<h3 class="font-bold">${stop.stop_type.charAt(0).toUpperCase() + stop.stop_type.slice(1)}</h3>`

          if (typeof stop.timestamp === "string" && stop.timestamp !== "0") {
            popupContent += `<p>Time: ${new Date(stop.timestamp).toLocaleString()}</p>`
          }

          if (stop.duration > 0) {
            popupContent += `<p>Duration: ${stop.duration} hours</p>`
          }

          popupContent += `<p>Coordinates: ${lat.toFixed(6)}, ${lng.toFixed(6)}</p>`

          // Add marker
          new mapboxgl.Marker({ color })
            .setLngLat([lng, lat])
            .setPopup(new mapboxgl.Popup().setHTML(popupContent))
            .addTo(map.current!)

          // Extend bounds
          bounds.extend([lng, lat])

          // Add waypoint to directions
          if (index === 0) {
            directions.setOrigin([lng, lat])
          } else if (index === stops.length - 1) {
            directions.setDestination([lng, lat])
          } else {
            directions.addWaypoint(index - 1, [lng, lat])
          }
        })

        // Fit bounds to include all stops
        map.current.fitBounds(bounds, { padding: 100 })
      } else {
        // Fallback to using the provided locations
        // Start marker
        new mapboxgl.Marker({ color: "#4F46E5" })
          .setLngLat(currentLocation)
          .setPopup(new mapboxgl.Popup().setHTML("<h3>Start</h3><p>Current Location</p>"))
          .addTo(map.current)

        // Pickup marker
        new mapboxgl.Marker({ color: "#F59E0B" })
          .setLngLat(pickupLocation)
          .setPopup(new mapboxgl.Popup().setHTML("<h3>Pickup</h3><p>Pickup Location</p>"))
          .addTo(map.current)

        // Dropoff marker
        new mapboxgl.Marker({ color: "#EF4444" })
          .setLngLat(dropoffLocation)
          .setPopup(new mapboxgl.Popup().setHTML("<h3>Destination</h3><p>Dropoff Location</p>"))
          .addTo(map.current)

        // Set directions
        directions.setOrigin(currentLocation)
        directions.setDestination(dropoffLocation)
        directions.addWaypoint(0, pickupLocation)

        // Fit bounds to include all points
        const bounds = new mapboxgl.LngLatBounds()
        bounds.extend(currentLocation)
        bounds.extend(pickupLocation)
        bounds.extend(dropoffLocation)
        map.current.fitBounds(bounds, { padding: 100 })
      }
    })

    // Clean up on unmount
    return () => {
      if (map.current) {
        map.current.remove()
      }
    }
  }, [stops, currentLocation, pickupLocation, dropoffLocation])

  return <div ref={mapContainer} className="w-full h-full" />
}

