import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useToast } from '@/hooks/use-toast'
import { Plus, Search, Download, Trash2, Eye, Loader2 } from 'lucide-react'
import TwinScaleService from '@/services/twinscaleService'
import { useTranslation } from 'react-i18next'

const TwinScaleThingList = () => {
  const { t } = useTranslation()
  const { toast } = useToast()
  const [interfaces, setInterfaces] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchFilter, setSearchFilter] = useState('')

  const loadInterfaces = async () => {
    setIsLoading(true)
    try {
      const data = await TwinScaleService.listInterfaces(
        searchFilter || null,
        100
      )
      setInterfaces(data.interfaces || [])
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

  useEffect(() => {
    loadInterfaces()
  }, [])

  const handleSearch = () => {
    loadInterfaces()
  }

  const handleExport = async (interfaceName) => {
    try {
      const blob = await TwinScaleService.exportAsZip(interfaceName)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${interfaceName}_twinscale.zip`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast({
        title: t('common.success'),
        description: t('things.exportSuccess') || 'YAML files exported successfully',
      })
    } catch (error) {
      toast({
        variant: 'destructive',
        title: t('common.error'),
        description: error.message,
      })
    }
  }

  const handleDelete = async (interfaceName) => {
    if (!confirm(t('things.deleteConfirm') || `Are you sure you want to delete "${interfaceName}"?`)) {
      return
    }

    try {
      await TwinScaleService.deleteInterface(interfaceName)
      toast({
        title: t('common.success'),
        description: t('things.deleteSuccess') || `Interface "${interfaceName}" deleted successfully`,
      })
      loadInterfaces()
    } catch (error) {
      toast({
        variant: 'destructive',
        title: t('common.error'),
        description: error.message,
      })
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">{t('things.title')}</h1>
        <Link to="/things/create">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            {t('things.create')}
          </Button>
        </Link>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <Input
              placeholder={t('things.searchPlaceholder')}
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              className="flex-1"
            />
            <Button onClick={handleSearch}>
              <Search className="mr-2 h-4 w-4" />
              {t('common.search')}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* List */}
      <Card>
        <CardHeader>
          <CardTitle>{t('things.list')} ({interfaces.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : interfaces.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {t('things.noThings')}
            </div>
          ) : (
            <div className="space-y-4">
              {interfaces.map((iface) => (
                <div
                  key={iface.interface || iface.name}
                  className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div>
                    <h3 className="font-medium">{iface.name}</h3>
                    {iface.description && (
                      <p className="text-sm text-muted-foreground">
                        {iface.description}
                      </p>
                    )}
                    {iface.generatedAt && (
                      <p className="text-xs text-muted-foreground mt-1">
                        {t('things.createdAt')}: {new Date(iface.generatedAt).toLocaleString()}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Link to={`/things/${iface.name}`}>
                      <Button variant="outline" size="sm">
                        <Eye className="h-4 w-4" />
                      </Button>
                    </Link>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExport(iface.name)}
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(iface.name)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default TwinScaleThingList
