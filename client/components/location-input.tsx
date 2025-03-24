"use client"

import type React from "react"

import { useState, useEffect, useRef } from "react"
import { MapPin } from "lucide-react"

const MAPBOX_TOKEN = "pk.eyJ1Ijoia2FtcGtlbGx5IiwiYSI6ImNtOGZvbmU3MDBlcDgybHB3YTRlMThyMXkifQ.rPz58hWmBPYkKtvN5uw9mA"

type LocationSuggestion = {
  id: string
  place_name: string
  center: [number, number] // [longitude, latitude]
}

type LocationInputProps = {
  id: string
  name: string
  label: string
  value: string
  placeholder: string
  onChange: (value: string, coordinates?: [number, number], placeName?: string) => void
  required?: boolean
}

export default function LocationInput({
  id,
  name,
  label,
  value,
  placeholder,
  onChange,
  required = false,
}: LocationInputProps) {
  const [suggestions, setSuggestions] = useState<LocationSuggestion[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const suggestionRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const fetchSuggestions = async () => {
      if (value.length < 2) {
        setSuggestions([])
        return
      }

      setIsLoading(true)
      try {
        const response = await fetch(
          `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(
            value,
          )}.json?access_token=${MAPBOX_TOKEN}&autocomplete=true&limit=5&types=place,address`,
        )
        const data = await response.json()
        setSuggestions(data.features || [])
      } catch (error) {
        console.error("Error fetching location suggestions:", error)
      } finally {
        setIsLoading(false)
      }
    }

    const debounceTimer = setTimeout(() => {
      fetchSuggestions()
    }, 300)

    return () => clearTimeout(debounceTimer)
  }, [value])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (suggestionRef.current && !suggestionRef.current.contains(event.target as Node)) {
        setShowSuggestions(false)
      }
    }

    document.addEventListener("mousedown", handleClickOutside)
    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value)
    setShowSuggestions(true)
  }

  const handleSuggestionClick = (suggestion: LocationSuggestion) => {
    onChange(suggestion.place_name, suggestion.center, suggestion.place_name)
    setShowSuggestions(false)
  }

  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
        {label}
      </label>
      <div className="relative" ref={suggestionRef}>
        <input
          type="text"
          id={id}
          name={name}
          value={value}
          onChange={handleInputChange}
          onFocus={() => value.length >= 2 && setShowSuggestions(true)}
          placeholder={placeholder}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-500"
          required={required}
        />
        <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none text-gray-400">
          <MapPin size={18} />
        </div>

        {showSuggestions && value.length >= 2 && (
          <div className="absolute z-10 w-full mt-1 bg-white rounded-md shadow-lg max-h-60 overflow-auto">
            {isLoading ? (
              <div className="p-2 text-sm text-gray-500">Loading suggestions...</div>
            ) : suggestions.length > 0 ? (
              <ul className="py-1">
                {suggestions.map((suggestion) => (
                  <li
                    key={suggestion.id}
                    className="px-3 py-2 text-sm hover:bg-gray-100 cursor-pointer"
                    onClick={() => handleSuggestionClick(suggestion)}
                  >
                    {suggestion.place_name}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="p-2 text-sm text-gray-500">No suggestions found</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
