import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useToast } from '@/hooks/use-toast'
import { ArrowLeft, Download, Trash2, Loader2, FileCode, RefreshCw, WifiOff, AlertTriangle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import TwinService from '@/services/twinService'

// Relationship tip renklerini döndürür
const REL_TYPE_COLORS = {
  feeds:      'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  isFedBy:    'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  controls:   'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  isControlledBy: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  contains:   'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  isContainedIn: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  monitors:   'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  isMonitoredBy: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  dependsOn:  'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  isDependedOnBy: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
}

const StatusBadge = ({ status }) => {
  if (status === 'Inactive') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400">
        <WifiOff className="h-3 w-3" />
        Inactive
      </span>
    )
  }
  if (status === 'Degraded') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300">
        <AlertTriangle className="h-3 w-3" />
        Degraded
      </span>
    )
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300">
      Active
    </span>
  )
}

const RelTypeBadge = ({ relType }) => {
  if (!relType) return null
  const colorClass = REL_TYPE_COLORS[relType] || 'bg-gray-100 text-gray-700'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
      {relType}
    </span>
  )
}

const TwinThingDetails = () => {
  const { interfaceName } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [interfaceData, setInterfaceData] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [dependencies, setDependencies] = useState(null)
  const [depsLoading, setDepsLoading] = useState(false)
  const [reactivating, setReactivating] = useState(null) // rel name being reactivated

  const loadDetails = async () => {
    setIsLoading(true)
    try {
      const data = await TwinService.getInterfaceDetails(interfaceName)
      setInterfaceData(data)
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.message,
      })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadDetails()
  }, [interfaceName])

  const handleExport = async () => {
    try {
      const blob = await TwinService.exportAsZip(interfaceName)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${interfaceName}_twin.zip`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Export Error',
        description: error.message,
      })
    }
  }

  const handleDeleteClick = async () => {
    setDepsLoading(true)
    try {
      const deps = await TwinService.getDependencies(interfaceName)
      setDependencies(deps)
    } catch {
      setDependencies({ forward_count: 0, inverse_count: 0, forward_targets: [], inverse_sources: [] })
    } finally {
      setDepsLoading(false)
    }
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = async () => {
    setDeleteDialogOpen(false)
    try {
      await TwinService.deleteInterface(interfaceName)
      toast({
        title: 'Silindi',
        description: `'${interfaceName}' başarıyla silindi`,
      })
      navigate('/things')
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Silme Hatası',
        description: error.message,
      })
    }
  }

  const handleReactivate = async (relName) => {
    setReactivating(relName)
    try {
      await TwinService.reactivateRelationship(interfaceName, relName)
      toast({
        title: 'Yeniden Bağlandı',
        description: `'${relName}' ilişkisi Active durumuna döndü`,
      })
      await loadDetails()
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Hata',
        description: error.message,
      })
    } finally {
      setReactivating(null)
    }
  }

  const handleRemoveRelationship = async (relName) => {
    if (!confirm(`'${relName}' ilişkisini tamamen kaldırmak istediğinize emin misiniz?`)) return
    toast({ title: 'Bilgi', description: 'Tek ilişki kaldırma henüz desteklenmiyor — thing silinerek tüm ilişkiler temizlenir.' })
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!interfaceData) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        Interface not found
      </div>
    )
  }

  // Outgoing: hem Active hem Inactive
  const activeOutgoing = (interfaceData.relationships || []).filter(r => r.status !== 'Inactive' && r.status !== 'Degraded')
  const inactiveOutgoing = (interfaceData.relationships || []).filter(r => r.status === 'Inactive' || r.status === 'Degraded')

  // Incoming: targetInterface = this
  const activeIncoming = (interfaceData.incomingRelationships || []).filter(r => r.status !== 'Inactive' && r.status !== 'Degraded')
  const inactiveIncoming = (interfaceData.incomingRelationships || []).filter(r => r.status === 'Inactive' || r.status === 'Degraded')

  const totalRelCount = (interfaceData.relationships?.length || 0) + (interfaceData.incomingRelationships?.length || 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => navigate('/things')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-2xl font-bold">{interfaceData.name}</h1>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            Export YAML
          </Button>
          <Button variant="destructive" onClick={handleDeleteClick} disabled={depsLoading}>
            {depsLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Trash2 className="mr-2 h-4 w-4" />}
            Sil
          </Button>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      {deleteDialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-background rounded-lg shadow-lg p-6 max-w-md w-full mx-4 space-y-4">
            <h2 className="text-lg font-semibold text-destructive flex items-center gap-2">
              <Trash2 className="h-5 w-5" />
              Thing'i Sil
            </h2>
            <p className="text-sm text-muted-foreground">
              <strong>{interfaceName}</strong> silinecek. Bu işlem geri alınamaz.
            </p>

            {dependencies && (dependencies.forward_count > 0 || dependencies.inverse_count > 0) && (
              <div className="border border-yellow-300 bg-yellow-50 dark:bg-yellow-950/30 dark:border-yellow-800 rounded-md p-3 space-y-2">
                <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300 flex items-center gap-1">
                  <AlertTriangle className="h-4 w-4" />
                  Aşağıdaki ilişkiler Inactive durumuna geçecek:
                </p>
                <ul className="text-xs space-y-1 text-yellow-700 dark:text-yellow-400">
                  {dependencies.inverse_sources.map((s, i) => (
                    <li key={i}>• <strong>{s.name}</strong> {s.type || s.relName} → this (Inactive olacak)</li>
                  ))}
                  {dependencies.forward_targets.map((t, i) => (
                    <li key={i}>• this {t.type || t.relName} → <strong>{t.name}</strong> (grafla birlikte silinecek)</li>
                  ))}
                </ul>
                <p className="text-xs text-yellow-600 dark:text-yellow-500 mt-1">
                  Bu thing'lerin diğer ilişkileri etkilenmeyecek.
                </p>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>İptal</Button>
              <Button variant="destructive" onClick={handleDeleteConfirm}>Evet, Sil</Button>
            </div>
          </div>
        </div>
      )}

      {interfaceData.description && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">{interfaceData.description}</p>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="properties">
        <TabsList>
          <TabsTrigger value="properties">
            Properties ({interfaceData.properties?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="relationships">
            Relationships ({totalRelCount})
          </TabsTrigger>
          <TabsTrigger value="commands">
            Commands ({interfaceData.commands?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="dtdl-binding">
            DTDL Binding
          </TabsTrigger>
        </TabsList>

        <TabsContent value="properties">
          <Card>
            <CardHeader><CardTitle>Properties</CardTitle></CardHeader>
            <CardContent>
              {interfaceData.properties?.length > 0 ? (
                <div className="space-y-4">
                  {interfaceData.properties.map((prop, index) => (
                    <div key={index} className="border rounded-md p-4">
                      <div className="flex justify-between">
                        <span className="font-medium">{prop.name}</span>
                        <span className="text-sm text-muted-foreground">{prop.type}</span>
                      </div>
                      {prop.description && (
                        <p className="text-sm text-muted-foreground mt-1">{prop.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">No properties defined</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="relationships">
          <Card>
            <CardHeader><CardTitle>Relationships</CardTitle></CardHeader>
            <CardContent className="space-y-6">

              {/* Outgoing — Active */}
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-3">
                  Outgoing — Active ({activeOutgoing.length})
                </h4>
                {activeOutgoing.length > 0 ? (
                  <div className="space-y-3">
                    {activeOutgoing.map((rel, index) => (
                      <div key={index} className="border rounded-md p-4">
                        <div className="flex justify-between items-center">
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge variant="outline">outgoing</Badge>
                            <RelTypeBadge relType={rel.relationshipType} />
                            <StatusBadge status={rel.status || 'Active'} />
                            <span className="font-medium">{rel.name}</span>
                          </div>
                          <span className="text-sm text-muted-foreground">
                            this → {rel.targetInterface}
                          </span>
                        </div>
                        {rel.description && (
                          <p className="text-sm text-muted-foreground mt-1">{rel.description}</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Aktif outgoing ilişki yok</p>
                )}
              </div>

              {/* Incoming — Active */}
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-3">
                  Incoming — Active ({activeIncoming.length})
                </h4>
                {activeIncoming.length > 0 ? (
                  <div className="space-y-3">
                    {activeIncoming.map((rel, index) => (
                      <div key={index} className="border rounded-md p-4 border-blue-200 bg-blue-50/50 dark:border-blue-900 dark:bg-blue-950/20">
                        <div className="flex justify-between items-center">
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge variant="secondary">incoming</Badge>
                            <RelTypeBadge relType={rel.relationshipType} />
                            <StatusBadge status={rel.status || 'Active'} />
                            <span className="font-medium">{rel.name}</span>
                          </div>
                          <span className="text-sm text-muted-foreground">
                            {rel.sourceInterface} → this
                          </span>
                        </div>
                        {rel.description && (
                          <p className="text-sm text-muted-foreground mt-1">{rel.description}</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Aktif incoming ilişki yok</p>
                )}
              </div>

              {/* Inactive Relationships */}
              {(inactiveOutgoing.length > 0 || inactiveIncoming.length > 0) && (
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-3">
                    Inactive / Kopuk İlişkiler ({inactiveOutgoing.length + inactiveIncoming.length})
                  </h4>
                  <div className="space-y-3">
                    {inactiveOutgoing.map((rel, index) => (
                      <div key={`out-${index}`} className="border rounded-md p-4 border-gray-200 bg-gray-50/50 dark:border-gray-700 dark:bg-gray-900/30 opacity-70">
                        <div className="flex justify-between items-center">
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge variant="outline">outgoing</Badge>
                            <RelTypeBadge relType={rel.relationshipType} />
                            <StatusBadge status={rel.status} />
                            <span className="font-medium line-through text-muted-foreground">{rel.name}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-muted-foreground">
                              this → {rel.targetInterface}
                            </span>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleReactivate(rel.name)}
                              disabled={reactivating === rel.name}
                            >
                              {reactivating === rel.name
                                ? <Loader2 className="h-3 w-3 animate-spin" />
                                : <RefreshCw className="h-3 w-3" />}
                              <span className="ml-1">Yeniden Bağla</span>
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleRemoveRelationship(rel.name)}
                              className="text-destructive"
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                    {inactiveIncoming.map((rel, index) => (
                      <div key={`in-${index}`} className="border rounded-md p-4 border-gray-200 bg-gray-50/50 dark:border-gray-700 dark:bg-gray-900/30 opacity-70">
                        <div className="flex justify-between items-center">
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge variant="secondary">incoming</Badge>
                            <RelTypeBadge relType={rel.relationshipType} />
                            <StatusBadge status={rel.status} />
                            <span className="font-medium line-through text-muted-foreground">{rel.name}</span>
                          </div>
                          <span className="text-sm text-muted-foreground">
                            {rel.sourceInterface} → this
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="commands">
          <Card>
            <CardHeader><CardTitle>Commands</CardTitle></CardHeader>
            <CardContent>
              {interfaceData.commands?.length > 0 ? (
                <div className="space-y-4">
                  {interfaceData.commands.map((cmd, index) => (
                    <div key={index} className="border rounded-md p-4">
                      <span className="font-medium">{cmd.name}</span>
                      {cmd.description && (
                        <p className="text-sm text-muted-foreground mt-1">{cmd.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">No commands defined</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="dtdl-binding">
          <Card>
            <CardHeader><CardTitle>DTDL Interface Binding</CardTitle></CardHeader>
            <CardContent>
              {interfaceData.annotations?.['dtdl-interface'] ? (
                <div className="space-y-4">
                  <div className="border rounded-lg p-4 bg-accent/50">
                    <h4 className="font-semibold text-lg mb-2">
                      {interfaceData.annotations['dtdl-interface-name'] || 'Unknown Interface'}
                    </h4>
                    <p className="text-xs text-muted-foreground font-mono mb-3">
                      {interfaceData.annotations['dtdl-interface']}
                    </p>
                    <div className="flex gap-2">
                      <Badge variant="secondary">
                        {interfaceData.annotations['dtdl-category'] || 'Unknown Category'}
                      </Badge>
                      <Badge variant="outline">
                        {interfaceData.labels?.['thing-type'] || 'atomic'}
                      </Badge>
                    </div>
                  </div>
                  <div>
                    <h5 className="text-sm font-semibold mb-3">Property Mapping</h5>
                    <div className="space-y-2">
                      {interfaceData.properties?.map((prop) => (
                        <div key={prop.name} className="flex items-center justify-between border rounded p-3">
                          <div>
                            <span className="font-medium text-sm">{prop.name}</span>
                            <span className="text-xs text-muted-foreground ml-2">({prop.type})</span>
                          </div>
                          <div className="flex items-center gap-2">
                            {prop.unit && (
                              <Badge variant="outline" className="text-xs">{prop.unit}</Badge>
                            )}
                            <Badge variant={prop.writable ? "default" : "secondary"} className="text-xs">
                              {prop.writable ? "Writable" : "Read-only"}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <FileCode className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No DTDL interface binding</p>
                  <p className="text-xs mt-2">This Thing was created without a DTDL interface</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default TwinThingDetails
