import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import Editor from '@monaco-editor/react'
import { useToast } from '@/hooks/use-toast'
import { Plus, Loader2, Check, Trash2, MapPin, Building2 } from 'lucide-react'
import TwinScaleService from '@/services/twinscaleService'
import MapComponent from '@/components/map/MapComponent'
import { useTranslation } from 'react-i18next'
import useTenantStore from '@/store/useTenantStore'
import { Alert, AlertDescription } from '@/components/ui/alert'

const CreateTwinScaleThing = () => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [isLoading, setIsLoading] = useState(false)

  // Tenant store
  const { currentTenant, fetchTenants } = useTenantStore()

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
    latitude: 39.9334, // Default Ankara
    longitude: 32.8597,
  })

  // YAML preview state
  const [interfaceYaml, setInterfaceYaml] = useState('')
  const [instanceYaml, setInstanceYaml] = useState('')

  // Initialize tenant on mount
  useEffect(() => {
    if (!currentTenant) {
      fetchTenants(true, true) // Use public endpoint for unauthenticated access
    }
  }, [currentTenant, fetchTenants])

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
      // Get the normalized ID (without tenant prefix for display)
      const cleanId = formData.id.includes(':')
        ? formData.id.split(':')[1]
        : formData.id

      const normalizedId = cleanId.toLowerCase().replace(/[^a-z0-9-]/g, '-')

      // Simple YAML preview generation
      const interfacePreview = `apiVersion: dtd.twinscale/v0
kind: TwinInterface
metadata:
  name: ems-iodt2-${normalizedId}
  ${currentTenant ? `labels:\n    tenant: ${currentTenant.tenant_id}` : ''}
spec:
  name: ems-iodt2-${normalizedId}
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
      setInstanceYaml(`apiVersion: dtd.twinscale/v0
kind: TwinInstance
metadata:
  name: ems-iodt2-${normalizedId}
  ${currentTenant ? `labels:\n    tenant: ${currentTenant.tenant_id}` : ''}
spec:
  name: ems-iodt2-${normalizedId}
  interface: ems-iodt2-${normalizedId}
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
      const result = await TwinScaleService.createTwinScaleThing(formData)
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

  const addRelationship = () => {
    setFormData({
      ...formData,
      relationships: [
        ...formData.relationships,
        { name: '', target_interface: '', description: '' },
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

  const handleMapClick = (event) => {
    const { lngLat } = event
    setFormData({
      ...formData,
      latitude: lngLat.lat,
      longitude: lngLat.lng
    })
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
                      className="w-full px-3 py-2 border rounded-md"
                      value={prop.type}
                      onChange={(e) => updateProperty(index, 'type', e.target.value)}
                    >
                      <option value="string">{t('createThing.typeString')}</option>
                      <option value="integer">{t('createThing.typeInteger')}</option>
                      <option value="float">{t('createThing.typeFloat')}</option>
                      <option value="boolean">{t('createThing.typeBoolean')}</option>
                      <option value="object">{t('createThing.typeObject')}</option>
                      <option value="array">{t('createThing.typeArray')}</option>
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
                {formData.relationships.map((rel, index) => (
                  <div key={index} className="border rounded-md p-3 space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium">Relationship {index + 1}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeRelationship(index)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                    <Input
                      placeholder="Relationship Name"
                      value={rel.name}
                      onChange={(e) => updateRelationship(index, 'name', e.target.value)}
                    />
                    <Input
                      placeholder="Target Interface (e.g., ems-iodt2-location)"
                      value={rel.target_interface}
                      onChange={(e) => updateRelationship(index, 'target_interface', e.target.value)}
                    />
                    <Input
                      placeholder="Description (optional)"
                      value={rel.description || ''}
                      onChange={(e) => updateRelationship(index, 'description', e.target.value)}
                    />
                  </div>
                ))}
                <Button variant="outline" onClick={addRelationship} className="w-full">
                  <Plus className="mr-2 h-4 w-4" />
                  Add Relationship
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
                    sensors={[{
                      id: 'new-location',
                      latitude: formData.latitude || 39.9334,
                      longitude: formData.longitude || 32.8597,
                      type: 'side_kozalak',
                      status: 'online',
                      name: t('createThing.selectedLocation')
                    }]}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">{t('createThing.latitude')}</label>
                    <Input
                      type="number"
                      step="any"
                      value={formData.latitude}
                      onChange={(e) => setFormData({ ...formData, latitude: parseFloat(e.target.value) })}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">{t('createThing.longitude')}</label>
                    <Input
                      type="number"
                      step="any"
                      value={formData.longitude}
                      onChange={(e) => setFormData({ ...formData, longitude: parseFloat(e.target.value) })}
                    />
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* Right: YAML Preview */}
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
                    height="500px"
                    defaultLanguage="yaml"
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
                    height="500px"
                    defaultLanguage="yaml"
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
      </div>
    </div>
  )
}

export default CreateTwinScaleThing
