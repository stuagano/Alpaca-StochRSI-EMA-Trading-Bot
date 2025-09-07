"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { 
  Zap, TrendingUp, TrendingDown, X, Keyboard, 
  Target, AlertTriangle, DollarSign 
} from "lucide-react"
import { formatPercent } from '@/lib/utils'

interface QuickActionPanelProps {
  selectedSymbol: string
  onQuickBuy: () => Promise<void>
  onQuickSell: () => Promise<void>
  onCloseAll: () => Promise<void>
  positionSize: number
  onPositionSizeChange: (size: number) => void
  hotkeysEnabled: boolean
  onHotkeysToggle: (enabled: boolean) => void
}

export function QuickActionPanel({
  selectedSymbol,
  onQuickBuy,
  onQuickSell,
  onCloseAll,
  positionSize,
  onPositionSizeChange,
  hotkeysEnabled,
  onHotkeysToggle
}: QuickActionPanelProps) {
  
  const presetSizes = [
    { label: "0.1%", value: 0.001 },
    { label: "0.5%", value: 0.005 },
    { label: "1%", value: 0.01 },
    { label: "2%", value: 0.02 }
  ]

  return (
    <Card className="border-2 border-orange-500/20">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Zap className="h-4 w-4 text-orange-500" />
          Quick Actions
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        
        {/* Quick Buy/Sell Buttons */}
        <div className="space-y-3">
          <Button 
            onClick={onQuickBuy}
            className="w-full h-12 text-base font-bold bg-green-600 hover:bg-green-700"
            disabled={!selectedSymbol}
          >
            <TrendingUp className="mr-2 h-5 w-5" />
            QUICK BUY {selectedSymbol}
          </Button>
          
          <Button 
            onClick={onQuickSell}
            variant="destructive"
            className="w-full h-12 text-base font-bold"
            disabled={!selectedSymbol}
          >
            <TrendingDown className="mr-2 h-5 w-5" />
            QUICK SELL {selectedSymbol}
          </Button>
        </div>

        <Separator />

        {/* Position Size Controls */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">Position Size</Label>
          
          <div className="grid grid-cols-2 gap-2">
            {presetSizes.map((preset) => (
              <Button
                key={preset.value}
                variant={positionSize === preset.value ? "default" : "outline"}
                size="sm"
                onClick={() => onPositionSizeChange(preset.value)}
                className="text-xs"
              >
                {preset.label}
              </Button>
            ))}
          </div>
          
          <div className="flex items-center gap-2">
            <Input
              type="number"
              value={positionSize * 100}
              onChange={(e) => onPositionSizeChange(parseFloat(e.target.value) / 100)}
              min="0.01"
              max="5"
              step="0.01"
              className="text-sm"
              placeholder="Custom %"
            />
            <Label className="text-xs text-muted-foreground whitespace-nowrap">
              % of account
            </Label>
          </div>
        </div>

        <Separator />

        {/* Emergency Controls */}
        <div className="space-y-3">
          <Button
            onClick={onCloseAll}
            variant="destructive"
            className="w-full"
            size="sm"
          >
            <X className="mr-2 h-4 w-4" />
            CLOSE ALL POSITIONS
          </Button>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Keyboard className="h-4 w-4" />
              <Label htmlFor="hotkeys" className="text-sm">Hotkeys</Label>
            </div>
            <Switch
              id="hotkeys"
              checked={hotkeysEnabled}
              onCheckedChange={onHotkeysToggle}
            />
          </div>
          
          {hotkeysEnabled && (
            <div className="p-2 bg-muted/30 rounded text-xs space-y-1">
              <div className="flex justify-between">
                <span>Quick Buy:</span>
                <Badge variant="outline" className="text-xs">SPACE</Badge>
              </div>
              <div className="flex justify-between">
                <span>Quick Sell:</span>
                <Badge variant="outline" className="text-xs">SHIFT + SPACE</Badge>
              </div>
              <div className="flex justify-between">
                <span>Close All:</span>
                <Badge variant="outline" className="text-xs">ESC</Badge>
              </div>
            </div>
          )}
        </div>

        {/* Risk Warning */}
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded">
          <div className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-xs font-medium">Scalping Risk Warning</span>
          </div>
          <p className="text-xs text-red-600/80 mt-1">
            High-frequency trading involves significant risk. Trade responsibly.
          </p>
        </div>

      </CardContent>
    </Card>
  )
}