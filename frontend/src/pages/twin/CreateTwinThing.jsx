import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import Editor from '@monaco-editor/react'
import { useToast } from '@/hooks/use-toast'
import { Plus, Loader2, Check, Trash2, MapPin, Building2, Layers, Info, FileCode, Wand2 } from 'lucide-react'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import TwinService from '@/services/twinService'
import MapComponent from '@/components/map/MapComponent'
import { useTranslation } from 'react-i18next'
import useTenantStore from '@/store/useTenantStore'
import { useTheme } from '@/components/theme-provider'
import { Alert, AlertDescription } from '@/components/ui/alert'
import DTDLSelectionModal from '@/components/dtdl/DTDLSelectionModal'
import DTDLValidationPanel from '@/components/dtdl/DTDLValidationPanel'

const CreateTwinThing = () => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [isLoading, setIsLoading] = useState(false)

  // Tenant store
  const { currentTenant, fetchTenants } = useTenantStore()

  // Theme — used for Monaco editor
  const { theme } = useTheme()
  const monacoTheme = theme === 'dark' ||
    (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
    ? 'vs-dark'
    : 'light'

  // Form state
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    description: '',
    properties: [],
    relationships: [],
    commands: [],
    include_service_spec: true,
    store_in_rdf: true,
    // Location Information
    latitude: null,
    longitude: null,
    address: '', // Physical address
    altitude: null, // Altitude/elevation in meters
    // NEW: Thing Type
    thing_type: 'atomic', // 'atomic', 'composite', 'system'
    // NEW: Domain Metadata
    manufacturer: '',
    model: '',
    serial_number: '',
    firmware_version: '',
    // NEW: DTDL Integration
    dtdl_interface: null, // Selected DTDL interface
    dtdl_interface_summary: null, // Interface summary for UI
  })

  // Available interfaces for relationship dropdown
  const [availableInterfaces, setAvailableInterfaces] = useState([])
  const [interfacesLoading, setInterfacesLoading] = useState(false)

  // DTDL Modal state
  const [showDTDLModal, setShowDTDLModal] = useState(false)

  // YAML preview state
  const [interfaceYaml, setInterfaceYaml] = useState('')
  const [instanceYaml, setInstanceYaml] = useState('')

  // Initialize tenant on mount
  useEffect(() => {
    if (!currentTenant) {
      fetchTenants(true, true) // Use public endpoint for unauthenticated access
    }
  }, [currentTenant, fetchTenants])

  // Load existing interfaces for relationship target dropdown — re-fetch when tenant changes
  useEffect(() => {
    const loadInterfaces = async () => {
      setInterfacesLoading(true)
      try {
        const result = await TwinService.listInterfaces()
        setAvailableInterfaces(result?.interfaces || [])
      } catch (error) {
        console.warn('Failed to load interfaces for relationship dropdown:', error)
        setAvailableInterfaces([])
      } finally {
        setInterfacesLoading(false)
      }
    }
    loadInterfaces()
  }, [currentTenant])

  // Auto-prefix Thing ID with tenant when user types
  const handleIdChange = (value) => {
    let finalId = value

    // If tenant exists and input doesn't already contain tenant prefix
    if (currentTenant && value && !value.includes(':')) {
      // Auto-format: tenant_id:value
      finalId = value
    }

    setFormData({ ...formData, id: finalId })
  }

  // Generate YAML preview when form changes
  useEffect(() => {
    if (formData.id && formData.name) {
      const tenantPrefix = currentTenant?.tenant_id
        ? currentTenant.tenant_id.toLowerCase().replace(/[^a-z0-9-]/g, '-')
        : 'default'

      // Strip tenant prefix if user accidentally typed it, then re-apply
      const rawId = formData.id.includes(':')
        ? formData.id.split(':')[1]
        : formData.id
      const cleanId = rawId.toLowerCase().replace(/[^a-z0-9-]/g, '-').replace(/^-+|-+$/g, '')
      const prefix = `${tenantPrefix}-`
      const normalizedName = cleanId.startsWith(prefix) ? cleanId : `${prefix}${cleanId}`

      // Build labels section
      const labelsSection = []
      if (currentTenant) {
        labelsSection.push(`    tenant: ${currentTenant.tenant_id}`)
      }
      labelsSection.push(`    thing-type: ${formData.thing_type}`)

      // Build annotations section
      const annotationsSection = []

      // Domain metadata
      if (formData.manufacturer) {
        annotationsSection.push(`    manufacturer: "${formData.manufacturer}"`)
      }
      if (formData.model) {
        annotationsSection.push(`    model: "${formData.model}"`)
      }
      if (formData.serial_number) {
        annotationsSection.push(`    serialNumber: "${formData.serial_number}"`)
      }
      if (formData.firmware_version) {
        annotationsSection.push(`    firmwareVersion: "${formData.firmware_version}"`)
      }

      // Location metadata
      if (formData.latitude != null && formData.latitude !== '') {
        annotationsSection.push(`    latitude: "${formData.latitude}"`)
      }
      if (formData.longitude != null && formData.longitude !== '') {
        annotationsSection.push(`    longitude: "${formData.longitude}"`)
      }
      if (formData.address && formData.address.trim() !== '') {
        annotationsSection.push(`    address: "${formData.address}"`)
      }
      if (formData.altitude != null && formData.altitude !== '') {
        annotationsSection.push(`    altitude: "${formData.altitude}"`)
      }

      // Simple YAML preview generation
      const interfacePreview = `apiVersion: dtd.twin/v0
kind: TwinInterface
metadata:
  name: ${normalizedName}
  labels:
${labelsSection.join('\n')}${annotationsSection.length > 0 ? `
  annotations:
${annotationsSection.join('\n')}` : ''}
spec:
  name: ${normalizedName}
  properties:
${formData.properties.map(p => `    - name: ${p.name}
      type: ${p.type}
      description: ${p.description || ''}
      x-writable: ${p.writable || false}`).join('\n') || '    []'}
  relationships:
${formData.relationships.map(r => `    - name: ${r.name}
      interface: ${r.target_interface}`).join('\n') || '    []'}
  commands:
${formData.commands.map(c => `    - name: ${c.name}
      description: ${c.description || ''}`).join('\n') || '    []'}`

      setInterfaceYaml(interfacePreview)

      // Instance YAML with labels
      const instanceLabelsSection = []
      if (currentTenant) {
        instanceLabelsSection.push(`    tenant: ${currentTenant.tenant_id}`)
      }
      instanceLabelsSection.push(`    thing-type: ${formData.thing_type}`)

      setInstanceYaml(`apiVersion: dtd.twin/v0
kind: TwinInstance
metadata:
  name: ${normalizedName}
  labels:
${instanceLabelsSection.join('\n')}
spec:
  name: ${normalizedName}
  interface: ${normalizedName}
  twinInstanceRelationships: []`)
    }
  }, [formData, currentTenant])

  const handleSubmit = async () => {
    // Tenant validation
    if (!currentTenant) {
      toast({
        variant: 'destructive',
        title: t('common.error'),
        description: 'Please select a tenant before creating a Thing',
      })
      return
    }

    if (!formData.id || !formData.name) {
      toast({
        variant: 'destructive',
        title: 'Validation Error',
        description: 'ID and Name are required',
      })
      return
    }

    setIsLoading(true)
    try {
      // Strip UI-only fields before sending to backend
      // Also normalize DTDL types to backend-accepted types
      const dtdlTypeMap = { double: 'float', long: 'integer', date: 'string', dateTime: 'string', duration: 'string', time: 'string' }
      const { dtdl_interface_summary, ...rest } = formData
      const payload = {
        ...rest,
        properties: formData.properties.map(({ isTelemetry, type, ...prop }) => ({
          ...prop,
          type: dtdlTypeMap[type] || type || 'string',
        })),
      }
      const result = await TwinService.createTwinThing(payload)
      toast({
        title: t('common.success'),
        description: t('createThing.createSuccess', { name: formData.name }),
      })
      navigate('/things')
    } catch (error) {
      toast({
        variant: 'destructive',
        title: t('common.error'),
        description: error.message,
      })
    } finally {
      setIsLoading(false)
    }
  }

  const addProperty = () => {
    setFormData({
      ...formData,
      properties: [
        ...formData.properties,
        { name: '', type: 'string', description: '', writable: false, unit: '', minimum: null, maximum: null },
      ],
    })
  }

  const removeProperty = (index) => {
    setFormData({
      ...formData,
      properties: formData.properties.filter((_, i) => i !== index),
    })
  }

  const updateProperty = (index, field, value) => {
    const newProperties = [...formData.properties]
    newProperties[index] = { ...newProperties[index], [field]: value }
    setFormData({ ...formData, properties: newProperties })
  }

  // DTDL Handlers
  const handleDTDLSelect = (selectedInterface, interfaceSummary) => {
    setFormData({
      ...formData,
      dtdl_interface: selectedInterface,
      dtdl_interface_summary: interfaceSummary,
    })
    toast({
      title: t('common.success'),
      description: t('dtdl.interfaceSelected', { name: selectedInterface.displayName }),
    })
  }

  const handleRemoveDTDL = () => {
    setFormData({
      ...formData,
      dtdl_interface: null,
      dtdl_interface_summary: null,
    })
  }

  const handleAutoFillFromDTDL = () => {
    if (!formData.dtdl_interface_summary) return

    const summary = formData.dtdl_interface_summary

    // Mevcut property ve command isimlerini set olarak tut — O(1) lookup
    const existingPropNames = new Set(formData.properties.map((p) => p.name))
    const existingCmdNames = new Set(formData.commands.map((c) => c.name))

    // Sadece henüz eklenmemiş property'leri al
    const newProperties = (summary.propertyDetails || [])
      .filter((prop) => !existingPropNames.has(prop.name))
      .map((prop) => ({
        name: prop.name,
        type: prop.type || 'string',
        description: prop.description || '',
        writable: prop.writable ?? true,
        unit: prop.unit || '',
        minimum: null,
        maximum: null,
      }))

    // Sadece henüz eklenmemiş telemetry'leri al
    const newTelemetry = (summary.telemetryDetails || [])
      .filter((tel) => !existingPropNames.has(tel.name))
      .map((tel) => ({
        name: tel.name,
        type: tel.type || 'float',
        description: tel.description || '',
        writable: false,
        unit: tel.unit || '',
        minimum: null,
        maximum: null,
        isTelemetry: true,
      }))

    // Sadece henüz eklenmemiş command'leri al
    const newCommands = (summary.commandDetails || [])
      .filter((cmd) => !existingCmdNames.has(cmd.name))
      .map((cmd) => ({
        name: cmd.name,
        description: cmd.description || '',
      }))

    const addedCount = newProperties.length + newTelemetry.length
    const skippedCount =
      (summary.propertyDetails?.length || 0) +
      (summary.telemetryDetails?.length || 0) -
      addedCount

    if (addedCount === 0 && newCommands.length === 0) {
      toast({
        title: t('common.info') || 'Bilgi',
        description: 'All DTDL fields have already been added.',
      })
      return
    }

    setFormData({
      ...formData,
      properties: [...formData.properties, ...newProperties, ...newTelemetry],
      commands: [...formData.commands, ...newCommands],
    })

    toast({
      title: t('common.success'),
      description: `${addedCount} property, ${newCommands.length} command eklendi${skippedCount > 0 ? ` (${skippedCount} zaten vardı, atlandı)` : ''}.`,
    })
  }

  const addRelationship = () => {
    setFormData({
      ...formData,
      relationships: [
        ...formData.relationships,
        { name: '', target_interface: '', description: '', relationship_type: 'feeds' },
      ],
    })
  }

  const removeRelationship = (index) => {
    setFormData({
      ...formData,
      relationships: formData.relationships.filter((_, i) => i !== index),
    })
  }

  const updateRelationship = (index, field, value) => {
    const newRelationships = [...formData.relationships]
    newRelationships[index] = { ...newRelationships[index], [field]: value }
    setFormData({ ...formData, relationships: newRelationships })
  }

  const addCommand = () => {
    setFormData({
      ...formData,
      commands: [
        ...formData.commands,
        { name: '', description: '' },
      ],
    })
  }

  const removeCommand = (index) => {
    setFormData({
      ...formData,
      commands: formData.commands.filter((_, i) => i !== index),
    })
  }

  const updateCommand = (index, field, value) => {
    const newCommands = [...formData.commands]
    newCommands[index] = { ...newCommands[index], [field]: value }
    setFormData({ ...formData, commands: newCommands })
  }

  const handleMapClick = async (event) => {
    const { lngLat } = event

    // Set coordinates immediately
    setFormData({
      ...formData,
      latitude: lngLat.lat,
      longitude: lngLat.lng
    })

    // Fetch address and altitude from location service
    try {
      const locationInfo = await TwinService.getLocationInfo(lngLat.lat, lngLat.lng)

      if (locationInfo) {
        setFormData(prevData => ({
          ...prevData,
          latitude: lngLat.lat,
          longitude: lngLat.lng,
          address: locationInfo.address || prevData.address,
          altitude: locationInfo.altitude != null ? locationInfo.altitude : prevData.altitude
        }))

        // Show success toast
        toast({
          title: t('common.success'),
          description: `Location updated: ${locationInfo.address || 'Address not found'}`,
        })
      }
    } catch (error) {
      console.error('Failed to fetch location info:', error)
      // Location already set with coordinates, so no error toast needed
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">{t('createThing.title')}</h1>
        <Button onClick={handleSubmit} disabled={isLoading || !currentTenant}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {t('createThing.creating')}
            </>
          ) : (
            <>
              <Check className="mr-2 h-4 w-4" />
              {t('createThing.createButton')}
            </>
          )}
        </Button>
      </div>

      {/* Tenant Information Banner */}
      {currentTenant ? (
        <Alert className="bg-blue-50 dark:bg-blue-950/50 border-blue-200 dark:border-blue-800">
          <Building2 className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          <AlertDescription className="flex items-center gap-2">
            <span className="font-medium text-blue-800 dark:text-blue-200">
              Creating Thing for Tenant:
            </span>
            <span className="font-semibold text-blue-900 dark:text-blue-100">
              {currentTenant.name || currentTenant.tenant_id}
            </span>
            <span className="text-xs text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/30 px-2 py-1 rounded">
              ID: {currentTenant.tenant_id}
            </span>
          </AlertDescription>
        </Alert>
      ) : (
        <Alert variant="destructive">
          <Building2 className="h-4 w-4" />
          <AlertDescription>
            No tenant selected. Please select a tenant from the navbar to create a Thing.
          </AlertDescription>
        </Alert>
      )}

      {/* Thing Type Selector */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Layers className="h-5 w-5" />
            {t('createThing.thingType')}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            {t('createThing.thingTypeDescription')}
          </p>
        </CardHeader>
        <CardContent>
          <RadioGroup
            value={formData.thing_type}
            onValueChange={(value) => setFormData({
              ...formData,
              thing_type: value,
              // Atomic dışı için device alanlarını temizle — bina/sistem'in manufacturer'ı olmaz
              ...(value !== 'atomic' && {
                manufacturer: '',
                model: '',
                serial_number: '',
                firmware_version: '',
              }),
            })}
            className="grid grid-cols-3 gap-4"
          >

            {/* Atomic Twin */}
            <div className="flex flex-col space-y-3 border rounded-lg p-4 hover:bg-accent transition-colors cursor-pointer h-full">
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="atomic" id="atomic" />
                <Label htmlFor="atomic" className="cursor-pointer font-semibold text-base">
                  ⚛️ {t('createThing.atomicTwinTitle')}
                </Label>
              </div>
              <div className="text-sm text-muted-foreground space-y-1 flex-1">
                <p>{t('createThing.atomicTwinDesc')}</p>
                <p className="text-xs italic">
                  <strong>{t('createThing.atomicTwinExampleLabel')}</strong> {t('createThing.atomicTwinExample')}
                </p>
                <div className="flex flex-wrap gap-1 mt-2">
                  <Badge variant="secondary" className="text-xs">SSN: sosa:Sensor / Platform</Badge>
                  <Badge variant="secondary" className="text-xs">Grieves: Atomic DT</Badge>
                </div>
              </div>
            </div>

            {/* Composite Twin */}
            <div className="flex flex-col space-y-3 border rounded-lg p-4 hover:bg-accent transition-colors cursor-pointer h-full">
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="composite" id="composite" />
                <Label htmlFor="composite" className="cursor-pointer font-semibold text-base">
                  🏗️ {t('createThing.compositeTwinTitle')}
                </Label>
              </div>
              <div className="text-sm text-muted-foreground space-y-1 flex-1">
                <p>{t('createThing.compositeTwinDesc')}</p>
                <p className="text-xs italic">
                  <strong>{t('createThing.atomicTwinExampleLabel')}</strong> {t('createThing.compositeTwinExample')}
                </p>
                <div className="flex flex-wrap gap-1 mt-2">
                  <Badge variant="secondary" className="text-xs">SSN: sosa:Platform</Badge>
                  <Badge variant="secondary" className="text-xs">Grieves: Composite DT</Badge>
                </div>
              </div>
            </div>

            {/* System Twin */}
            <div className="flex flex-col space-y-3 border rounded-lg p-4 hover:bg-accent transition-colors cursor-pointer h-full">
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="system" id="system" />
                <Label htmlFor="system" className="cursor-pointer font-semibold text-base">
                  🌐 {t('createThing.systemTwinTitle')}
                </Label>
              </div>
              <div className="text-sm text-muted-foreground space-y-1 flex-1">
                <p>{t('createThing.systemTwinDesc')}</p>
                <p className="text-xs italic">
                  <strong>{t('createThing.atomicTwinExampleLabel')}</strong> {t('createThing.systemTwinExample')}
                </p>
                <div className="flex flex-wrap gap-1 mt-2">
                  <Badge variant="secondary" className="text-xs">SSN: sosa:System</Badge>
                  <Badge variant="secondary" className="text-xs">Grieves: System DT</Badge>
                </div>
              </div>
            </div>
          </RadioGroup>

          {/* Info Alert */}
          <Alert className="mt-4">
            <Info className="h-4 w-4" />
            <AlertDescription className="text-xs">
              <strong>{t('createThing.grievesHierarchyLabel')}</strong> {t('createThing.grievesHierarchyDesc')}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      {/* DTDL Interface Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileCode className="h-5 w-5" />
            {t('dtdl.useDTDL')}
            <Badge variant="outline" className="ml-auto">Optional</Badge>
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            {t('dtdl.useDTDLDescription')}
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {!formData.dtdl_interface ? (
            <div className="border-2 border-dashed rounded-lg p-6 text-center">
              <FileCode className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
              <p className="text-sm text-muted-foreground mb-4">
                {t('dtdl.noInterfaceSelected')}
              </p>
              <Button
                onClick={() => setShowDTDLModal(true)}
                variant="outline"
                className="gap-2"
              >
                <FileCode className="h-4 w-4" />
                {t('dtdl.selectInterface')}
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="border rounded-lg p-4 bg-accent/50">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h4 className="font-semibold text-base">{formData.dtdl_interface.displayName}</h4>
                    <p className="text-xs text-muted-foreground font-mono mt-1">
                      {formData.dtdl_interface.dtmi}
                    </p>
                  </div>
                  <Button
                    onClick={handleRemoveDTDL}
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                <p className="text-sm text-muted-foreground mb-3">
                  {formData.dtdl_interface.description}
                </p>

                {formData.dtdl_interface_summary && (
                  <div className="grid grid-cols-4 gap-2 mb-3">
                    <div className="bg-background rounded p-2 text-center">
                      <div className="text-lg font-bold text-blue-600">
                        {formData.dtdl_interface_summary.telemetryCount}
                      </div>
                      <div className="text-xs text-muted-foreground">{t('dtdl.telemetry')}</div>
                    </div>
                    <div className="bg-background rounded p-2 text-center">
                      <div className="text-lg font-bold text-green-600">
                        {formData.dtdl_interface_summary.propertyCount}
                      </div>
                      <div className="text-xs text-muted-foreground">{t('dtdl.properties')}</div>
                    </div>
                    <div className="bg-background rounded p-2 text-center">
                      <div className="text-lg font-bold text-purple-600">
                        {formData.dtdl_interface_summary.commandCount}
                      </div>
                      <div className="text-xs text-muted-foreground">{t('dtdl.commands')}</div>
                    </div>
                    <div className="bg-background rounded p-2 text-center">
                      <div className="text-lg font-bold text-orange-600">
                        {formData.dtdl_interface_summary.componentCount}
                      </div>
                      <div className="text-xs text-muted-foreground">{t('dtdl.components')}</div>
                    </div>
                  </div>
                )}

                <div className="flex gap-2">
                  <Button
                    onClick={() => setShowDTDLModal(true)}
                    variant="outline"
                    size="sm"
                    className="flex-1"
                  >
                    {t('dtdl.changeInterface')}
                  </Button>
                  <Button
                    onClick={handleAutoFillFromDTDL}
                    variant="default"
                    size="sm"
                    className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-md hover:shadow-lg transition-all duration-200"
                    disabled={
                      !formData.dtdl_interface_summary?.propertyNames?.length &&
                      !formData.dtdl_interface_summary?.telemetryNames?.length &&
                      !formData.dtdl_interface_summary?.commandNames?.length
                    }
                  >
                    <Wand2 className="mr-2 h-4 w-4" />
                    {t('dtdl.autoFill')}
                  </Button>
                </div>
              </div>

              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription className="text-xs">
                  {t('dtdl.autoFillDescription')}
                </AlertDescription>
              </Alert>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-6">
        {/* Left: Form */}
        <Card>
          <CardHeader>
            <CardTitle>{t('createThing.thingDefinition')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('createThing.idRequired')}</label>
              <Input
                placeholder={currentTenant ? `${currentTenant.tenant_id}:thing1 or just thing1` : t('createThing.idPlaceholder')}
                value={formData.id}
                onChange={(e) => handleIdChange(e.target.value)}
              />
              {currentTenant && formData.id && !formData.id.includes(':') && (
                <p className="text-xs text-muted-foreground">
                  Will be saved as: <span className="font-mono font-semibold">{currentTenant.tenant_id}:{formData.id}</span>
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">{t('createThing.nameRequired')}</label>
              <Input
                placeholder={t('createThing.namePlaceholder')}
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">{t('createThing.description')}</label>
              <Textarea
                placeholder={t('createThing.descriptionPlaceholder')}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </div>

            {/* Domain Metadata Section — yalnız Atomic Twin için anlamlı (fiziksel cihaz) */}
            {formData.thing_type === 'atomic' && (
              <div className="border-t pt-4 mt-4">
                <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <Building2 className="h-4 w-4" />
                  {t('createThing.domainMetadata')}
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">{t('createThing.manufacturer')}</label>
                    <Input
                      placeholder={t('createThing.manufacturerPlaceholder')}
                      value={formData.manufacturer}
                      onChange={(e) => setFormData({ ...formData, manufacturer: e.target.value })}
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">{t('createThing.model')}</label>
                    <Input
                      placeholder={t('createThing.modelPlaceholder')}
                      value={formData.model}
                      onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">{t('createThing.serialNumber')}</label>
                    <Input
                      placeholder={t('createThing.serialNumberPlaceholder')}
                      value={formData.serial_number}
                      onChange={(e) => setFormData({ ...formData, serial_number: e.target.value })}
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">
                      {t('createThing.firmwareVersion')}
                      <span className="text-muted-foreground ml-1">({t('common.optional')})</span>
                    </label>
                    <Input
                      placeholder={t('createThing.firmwareVersionPlaceholder')}
                      value={formData.firmware_version}
                      onChange={(e) => setFormData({ ...formData, firmware_version: e.target.value })}
                    />
                  </div>
                </div>
              </div>
            )}

            <Tabs defaultValue="properties">
              <TabsList className="w-full grid grid-cols-4">
                <TabsTrigger value="properties">
                  {t('createThing.properties')} ({formData.properties.length})
                </TabsTrigger>
                <TabsTrigger value="relationships">
                  Relationships ({formData.relationships.length})
                </TabsTrigger>
                <TabsTrigger value="commands">
                  {t('createThing.commands')} ({formData.commands.length})
                </TabsTrigger>
                <TabsTrigger value="location">
                  {t('createThing.location')}
                </TabsTrigger>
              </TabsList>

              <TabsContent value="properties" className="space-y-4">
                {formData.properties.map((prop, index) => (
                  <div key={index} className="border rounded-md p-3 space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium">{t('createThing.property')} {index + 1}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeProperty(index)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                    <Input
                      placeholder={t('createThing.propertyName')}
                      value={prop.name}
                      onChange={(e) => updateProperty(index, 'name', e.target.value)}
                    />
                    <select
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      value={prop.type}
                      onChange={(e) => updateProperty(index, 'type', e.target.value)}
                    >
                      <option value="string" className="bg-background text-foreground">{t('createThing.typeString')}</option>
                      <option value="integer" className="bg-background text-foreground">{t('createThing.typeInteger')}</option>
                      <option value="float" className="bg-background text-foreground">{t('createThing.typeFloat')}</option>
                      <option value="boolean" className="bg-background text-foreground">{t('createThing.typeBoolean')}</option>
                      <option value="object" className="bg-background text-foreground">{t('createThing.typeObject')}</option>
                      <option value="array" className="bg-background text-foreground">{t('createThing.typeArray')}</option>
                    </select>
                    <Input
                      placeholder={t('createThing.propertyDescription')}
                      value={prop.description}
                      onChange={(e) => updateProperty(index, 'description', e.target.value)}
                    />
                    <div className="flex items-center gap-2">
                      <label className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={prop.writable || false}
                          onChange={(e) => updateProperty(index, 'writable', e.target.checked)}
                          className="rounded"
                        />
                        Writable
                      </label>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <Input
                        type="number"
                        placeholder="Min"
                        value={prop.minimum || ''}
                        onChange={(e) => updateProperty(index, 'minimum', e.target.value ? parseFloat(e.target.value) : null)}
                      />
                      <Input
                        type="number"
                        placeholder="Max"
                        value={prop.maximum || ''}
                        onChange={(e) => updateProperty(index, 'maximum', e.target.value ? parseFloat(e.target.value) : null)}
                      />
                      <Input
                        placeholder="Unit"
                        value={prop.unit || ''}
                        onChange={(e) => updateProperty(index, 'unit', e.target.value)}
                      />
                    </div>
                  </div>
                ))}
                <Button variant="outline" onClick={addProperty} className="w-full">
                  <Plus className="mr-2 h-4 w-4" />
                  {t('createThing.addProperty')}
                </Button>
              </TabsContent>

              <TabsContent value="relationships" className="space-y-4">
                {/* Relationships explanation banner */}
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription className="text-sm">
                    {t('createThing.relationshipsHint')}
                  </AlertDescription>
                </Alert>

                {formData.relationships.map((rel, index) => (
                  <div key={index} className="border rounded-md p-3 space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium">
                        {t('createThing.relationship')} {index + 1}
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeRelationship(index)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>

                    {/* Relationship type — first so the user picks the semantic before naming */}
                    <Select
                      value={rel.relationship_type || 'feeds'}
                      onValueChange={(value) => updateRelationship(index, 'relationship_type', value)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder={t('createThing.relationshipTypePlaceholder')} />
                      </SelectTrigger>
                      <SelectContent className="bg-popover border shadow-md z-50">
                        <SelectItem value="feeds">
                          <span className="font-mono text-xs font-semibold text-primary mr-2">feeds</span>
                          <span className="text-muted-foreground">{t('createThing.relFeedsDesc')}</span>
                        </SelectItem>
                        <SelectItem value="controls">
                          <span className="font-mono text-xs font-semibold text-primary mr-2">controls</span>
                          <span className="text-muted-foreground">{t('createThing.relControlsDesc')}</span>
                        </SelectItem>
                        <SelectItem value="contains">
                          <span className="font-mono text-xs font-semibold text-primary mr-2">contains</span>
                          <span className="text-muted-foreground">{t('createThing.relContainsDesc')}</span>
                        </SelectItem>
                        <SelectItem value="monitors">
                          <span className="font-mono text-xs font-semibold text-primary mr-2">monitors</span>
                          <span className="text-muted-foreground">{t('createThing.relMonitorsDesc')}</span>
                        </SelectItem>
                        <SelectItem value="dependsOn">
                          <span className="font-mono text-xs font-semibold text-primary mr-2">dependsOn</span>
                          <span className="text-muted-foreground">{t('createThing.relDependsOnDesc')}</span>
                        </SelectItem>
                      </SelectContent>
                    </Select>

                    {/* Target twin */}
                    <Select
                      value={rel.target_interface}
                      onValueChange={(value) => updateRelationship(index, 'target_interface', value)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder={
                          interfacesLoading
                            ? t('createThing.relationshipTargetLoading')
                            : availableInterfaces.length === 0
                              ? t('createThing.relationshipTargetEmpty')
                              : t('createThing.relationshipTargetPlaceholder')
                        } />
                      </SelectTrigger>
                      <SelectContent className="bg-popover border shadow-md z-50">
                        {availableInterfaces.map((iface) => (
                          <SelectItem key={iface.name} value={iface.name}>
                            {iface.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    {/* Optional name — shown after type+target so user has context */}
                    <Input
                      placeholder={t('createThing.relationshipNamePlaceholder')}
                      value={rel.name}
                      onChange={(e) => updateRelationship(index, 'name', e.target.value)}
                    />

                    <Input
                      placeholder={t('createThing.relationshipDescription')}
                      value={rel.description || ''}
                      onChange={(e) => updateRelationship(index, 'description', e.target.value)}
                    />
                  </div>
                ))}

                <Button variant="outline" onClick={addRelationship} className="w-full">
                  <Plus className="mr-2 h-4 w-4" />
                  {t('createThing.addRelationship')}
                </Button>
              </TabsContent>

              <TabsContent value="commands" className="space-y-4">
                {formData.commands.map((cmd, index) => (
                  <div key={index} className="border rounded-md p-3 space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium">{t('createThing.command')} {index + 1}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeCommand(index)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                    <Input
                      placeholder={t('createThing.commandName')}
                      value={cmd.name}
                      onChange={(e) => updateCommand(index, 'name', e.target.value)}
                    />
                    <Input
                      placeholder={t('createThing.commandDescription')}
                      value={cmd.description}
                      onChange={(e) => updateCommand(index, 'description', e.target.value)}
                    />
                  </div>
                ))}
                <Button variant="outline" onClick={addCommand} className="w-full">
                  <Plus className="mr-2 h-4 w-4" />
                  {t('createThing.addCommand')}
                </Button>
              </TabsContent>

              <TabsContent value="location" className="space-y-4">
                <div className="h-[400px] w-full border rounded-md overflow-hidden relative">
                  <MapComponent
                    center={{ lat: formData.latitude || 39.9334, lng: formData.longitude || 32.8597 }}
                    zoom={15}
                    onMapClick={handleMapClick}
                    sensors={formData.latitude != null && formData.longitude != null ? [{
                      id: 'new-location',
                      latitude: formData.latitude,
                      longitude: formData.longitude,
                      type: 'secondary',
                      status: 'online',
                      name: t('createThing.selectedLocation')
                    }] : []}
                  />
                </div>
                <div className="space-y-4">
                  {/* Coordinates */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">
                        {t('createThing.latitude')}
                        <span className="text-muted-foreground ml-1">({t('common.optional')})</span>
                      </label>
                      <Input
                        type="number"
                        step="any"
                        placeholder="e.g., 39.9334"
                        value={formData.latitude || ''}
                        onChange={(e) => setFormData({ ...formData, latitude: e.target.value ? parseFloat(e.target.value) : null })}
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">
                        {t('createThing.longitude')}
                        <span className="text-muted-foreground ml-1">({t('common.optional')})</span>
                      </label>
                      <Input
                        type="number"
                        step="any"
                        placeholder="e.g., 32.8597"
                        value={formData.longitude || ''}
                        onChange={(e) => setFormData({ ...formData, longitude: e.target.value ? parseFloat(e.target.value) : null })}
                      />
                    </div>
                  </div>

                  {/* Address and Altitude */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">
                        {t('createThing.address')}
                        <span className="text-muted-foreground ml-1">({t('common.optional')})</span>
                      </label>
                      <Input
                        type="text"
                        placeholder={t('createThing.addressPlaceholder')}
                        value={formData.address || ''}
                        onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">
                        {t('createThing.altitude')}
                        <span className="text-muted-foreground ml-1">({t('common.optional')})</span>
                      </label>
                      <Input
                        type="number"
                        step="any"
                        placeholder={t('createThing.altitudePlaceholder')}
                        value={formData.altitude || ''}
                        onChange={(e) => setFormData({ ...formData, altitude: e.target.value ? parseFloat(e.target.value) : null })}
                      />
                    </div>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* Right: YAML Preview & Validation */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>{t('createThing.yamlPreview')}</CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="interface">
                <TabsList className="w-full mb-4">
                  <TabsTrigger value="interface" className="flex-1">
                    {t('createThing.interfaceYaml')}
                  </TabsTrigger>
                  <TabsTrigger value="instance" className="flex-1">
                    {t('createThing.instanceYaml')}
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="interface">
                  <div className="border rounded-md overflow-hidden">
                    <Editor
                      height="400px"
                      defaultLanguage="yaml"
                      theme={monacoTheme}
                      value={interfaceYaml}
                      options={{
                        minimap: { enabled: false },
                        readOnly: true,
                        wordWrap: 'on',
                        lineNumbers: 'on',
                      }}
                    />
                  </div>
                </TabsContent>

                <TabsContent value="instance">
                  <div className="border rounded-md overflow-hidden">
                    <Editor
                      height="400px"
                      defaultLanguage="yaml"
                      theme={monacoTheme}
                      value={instanceYaml}
                      options={{
                        minimap: { enabled: false },
                        readOnly: true,
                        wordWrap: 'on',
                        lineNumbers: 'on',
                      }}
                    />
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          {/* DTDL Validation Panel */}
          {formData.dtdl_interface && (
            <DTDLValidationPanel
              formData={formData}
              dtdlInterface={formData.dtdl_interface}
            />
          )}
        </div>
      </div>

      {/* DTDL Selection Modal */}
      <DTDLSelectionModal
        isOpen={showDTDLModal}
        onClose={() => setShowDTDLModal(false)}
        onSelect={handleDTDLSelect}
        thingType={null}
        domain={null}
      />
    </div>
  )
}

export default CreateTwinThing
