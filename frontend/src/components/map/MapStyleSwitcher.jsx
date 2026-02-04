import React, { useState } from 'react'
import { Card, CardContent } from '../ui/card'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover'
import { 
  Map, 
  Palette, 
  Sun, 
  Moon, 
  Satellite, 
  Mountain, 
  Check,
  ChevronDown
} from 'lucide-react'

const MapStyleSwitcher = ({
  availableStyles = [],
  currentStyle,
  onStyleChange,
  position = 'top-right',
  showPreviews = true,
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false)

  // Get current style info
  const getCurrentStyleInfo = () => {
    return availableStyles.find(style => style.url === currentStyle) || availableStyles[0]
  }

  // Get category icon
  const getCategoryIcon = (category) => {
    switch (category) {
      case 'light':
        return <Sun className="w-3 h-3" />
      case 'dark':
        return <Moon className="w-3 h-3" />
      case 'satellite':
        return <Satellite className="w-3 h-3" />
      case 'terrain':
        return <Mountain className="w-3 h-3" />
      default:
        return <Map className="w-3 h-3" />
    }
  }

  // Get position classes
  const getPositionClasses = () => {
    const baseClasses = 'absolute z-50'
    
    switch (position) {
      case 'top-left':
        return `${baseClasses} top-4 left-4`
      case 'top-right':
        return `${baseClasses} top-4 right-4`
      case 'bottom-left':
        return `${baseClasses} bottom-4 left-4`
      case 'bottom-right':
        return `${baseClasses} bottom-4 right-4`
      default:
        return `${baseClasses} top-4 right-4`
    }
  }

  const handleStyleChange = (style) => {
    onStyleChange?.(style.url)
    setIsOpen(false)
  }

  const currentStyleInfo = getCurrentStyleInfo()

  if (!availableStyles || availableStyles.length === 0) {
    return null
  }

  return (
    <div className={`${getPositionClasses()} ${className}`}>
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="bg-white/90 backdrop-blur-sm border-gray-200 shadow-sm hover:bg-white"
          >
            <div className="flex items-center space-x-2">
              {getCategoryIcon(currentStyleInfo?.category)}
              <span className="text-xs font-medium">
                {currentStyleInfo?.name || 'Map Style'}
              </span>
              <ChevronDown className="w-3 h-3" />
            </div>
          </Button>
        </PopoverTrigger>
        
        <PopoverContent 
          className="w-80 p-3" 
          align={position.includes('right') ? 'end' : 'start'}
        >
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <Palette className="w-4 h-4 text-gray-600" />
              <h3 className="font-medium text-sm">Map Styles</h3>
            </div>
            
            <div className="space-y-2">
              {availableStyles.map((style) => (
                <div
                  key={style.id}
                  className={`
                    group flex items-center space-x-3 p-3 rounded-lg cursor-pointer transition-all
                    ${currentStyle === style.url 
                      ? 'bg-blue-50 border border-blue-200' 
                      : 'hover:bg-gray-50 border border-transparent'
                    }
                  `}
                  onClick={() => handleStyleChange(style)}
                >
                  {showPreviews && (
                    <div className="relative">
                      <div className="w-12 h-8 bg-gray-100 rounded border overflow-hidden">
                        {/* Placeholder for preview image */}
                        <div className={`
                          w-full h-full flex items-center justify-center text-xs
                          ${style.category === 'dark' ? 'bg-gray-800 text-white' :
                            style.category === 'satellite' ? 'bg-green-200 text-green-800' :
                            'bg-blue-50 text-blue-600'}
                        `}>
                          {getCategoryIcon(style.category)}
                        </div>
                      </div>
                      
                      {currentStyle === style.url && (
                        <div className="absolute -top-1 -right-1 w-4 h-4 bg-blue-500 rounded-full flex items-center justify-center">
                          <Check className="w-2 h-2 text-white" />
                        </div>
                      )}
                    </div>
                  )}
                  
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium text-sm">{style.name}</h4>
                        <div className="flex items-center space-x-1 mt-1">
                          <Badge 
                            variant="secondary" 
                            className="text-xs px-2 py-0"
                          >
                            {style.category}
                          </Badge>
                        </div>
                      </div>
                      
                      {!showPreviews && currentStyle === style.url && (
                        <Check className="w-4 h-4 text-blue-500" />
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            
            <div className="border-t pt-2">
              <p className="text-xs text-gray-500">
                Click on any style to change the map appearance instantly
              </p>
            </div>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  )
}

export default MapStyleSwitcher