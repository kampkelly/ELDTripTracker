"use client"

import { useEffect, useRef } from "react"
import mapboxgl from "mapbox-gl"
import "mapbox-gl/dist/mapbox-gl.css"
import MapboxDirections from "@mapbox/mapbox-gl-directions/dist/mapbox-gl-directions"
import "@mapbox/mapbox-gl-directions/dist/mapbox-gl-directions.css"

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

const getMarkerColor = (stopType: string): string => {
  switch (stopType.toLowerCase()) {
    case "current location":
      return "#4F46E5"
    case "pickup":
      return "#F59E0B"
    case "dropoff":
      return "#EF4444"
    case "rest break":
      return "#10B981"
    case "fuel":
      return "#8B5CF6"
    default:
      return "#6B7280"
  }
}

export default function MapboxMap({
  stops = [],
  currentLocation = [-87.63924407958984, 41.87867736816406],
  pickupLocation = [-83.74621216, 32.26003672],
  dropoffLocation = [-80.19515228271484, 25.774606704711914],
}: MapboxMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<mapboxgl.Map | null>(null)

  useEffect(() => {
    if (!mapContainer.current) return

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: "mapbox://styles/mapbox/streets-v12",
      center: stops[0].coordinates,
      zoom: 5,
      accessToken: MAPBOX_TOKEN,
    })

    const directions = new MapboxDirections({
      accessToken: MAPBOX_TOKEN,
      profile: "mapbox/driving",
      alternatives: false,
      unit: "metric",
      interactive: false,
      instructions: {
        showWaypointInstructions: true,
      },
      controls: {
        inputs: true,
        instructions: true,
        profileSwitcher: false,
      },
    })

    map.current.addControl(new mapboxgl.NavigationControl(), "top-right")
    map.current.addControl(directions, "top-left")
    map.current.setConfigProperty("basemap", "show3dObjects", true)
    map.current.setConfigProperty("basemap", "colorTrunks", "red")

    map.current.on("load", () => {
      if (!map.current) return

      if (stops && stops.length > 0) {
        const bounds = new mapboxgl.LngLatBounds()

        stops.forEach((stop, index) => {
          const [lng, lat] = stop.coordinates
          const color = getMarkerColor(stop.stop_type)

          let popupContent = `<h3 class="font-bold">${stop.stop_type.charAt(0).toUpperCase() + stop.stop_type.slice(1)}</h3>`

          if (typeof stop.timestamp === "string" && stop.timestamp !== "0") {
            popupContent += `<p>Time: ${new Date(stop.timestamp).toLocaleString()}</p>`
          }

          if (stop.duration > 0) {
            popupContent += `<p>Duration: ${stop.duration} hours</p>`
          }

          popupContent += `<p>Coordinates: ${lat.toFixed(6)}, ${lng.toFixed(6)}</p>`

          new mapboxgl.Marker({ color })
            .setLngLat([lng, lat])
            .setPopup(new mapboxgl.Popup().setHTML(popupContent))
            .addTo(map.current!)

          bounds.extend([lng, lat])

          if (index === 0) {
            directions.setOrigin([lng, lat])
          } else if (index === stops.length - 1) {
            directions.setDestination([lng, lat])
          } else {
            directions.addWaypoint(index - 1, [lng, lat])
          }
        })

        map.current.fitBounds(bounds, { padding: 100 })
      } else {
        new mapboxgl.Marker({ color: "#4F46E5" })
          .setLngLat(currentLocation)
          .setPopup(new mapboxgl.Popup().setHTML("<h3>Start</h3><p>Current Location</p>"))
          .addTo(map.current)

        new mapboxgl.Marker({ color: "#F59E0B" })
          .setLngLat(pickupLocation)
          .setPopup(new mapboxgl.Popup().setHTML("<h3>Pickup</h3><p>Pickup Location</p>"))
          .addTo(map.current)

        new mapboxgl.Marker({ color: "#EF4444" })
          .setLngLat(dropoffLocation)
          .setPopup(new mapboxgl.Popup().setHTML("<h3>Destination</h3><p>Dropoff Location</p>"))
          .addTo(map.current)

        directions.setOrigin(currentLocation)
        directions.setDestination(dropoffLocation)
        directions.addWaypoint(0, pickupLocation)

        const bounds = new mapboxgl.LngLatBounds()
        bounds.extend(currentLocation)
        bounds.extend(pickupLocation)
        bounds.extend(dropoffLocation)
        map.current.fitBounds(bounds, { padding: 100 })
      }
    })

    return () => {
      if (map.current) {
        map.current.remove()
      }
    }
  }, [stops, currentLocation, pickupLocation, dropoffLocation])

  return <div ref={mapContainer} className="w-full h-full" />
}
