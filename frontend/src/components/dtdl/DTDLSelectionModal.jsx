/**
 * DTDL Selection Modal Component
 *
 * Modal for browsing, searching, and selecting DTDL interfaces.
 * Includes filtering, search, and interface detail view.
 */

import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { X, Search, Filter, Info, CheckCircle } from 'lucide-react'
import { listInterfaces, getInterfaceSummary } from '../../api/dtdl'

const DTDLSelectionModal = ({ isOpen, onClose, onSelect, thingType = null, domain = null }) => {
  const { t } = useTranslation()
  const [interfaces, setInterfaces] = useState([])
  const [filteredInterfaces, setFilteredInterfaces] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Filters
  const [searchKeyword, setSearchKeyword] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [selectedDomain, setSelectedDomain] = useState(domain || 'all')

  // Selected interface
  const [selectedInterface, setSelectedInterface] = useState(null)
  const [interfaceSummary, setInterfaceSummary] = useState(null)
  const [loadingSummary, setLoadingSummary] = useState(false)

  // Load interfaces on mount or when filters change
  useEffect(() => {
    if (isOpen) {
      loadInterfaces()
    }
  }, [isOpen, thingType])

  // Apply local filters
  useEffect(() => {
    applyFilters()
  }, [interfaces, searchKeyword, selectedCategory, selectedDomain])

  const loadInterfaces = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (thingType && thingType !== 'all') {
        params.thing_type = thingType
      }
      const data = await listInterfaces(params)
      setInterfaces(data.interfaces || [])
    } catch (err) {
      console.error('Failed to load DTDL interfaces:', err)
      setError(t('dtdl.errorLoadingInterfaces'))
    } finally {
      setLoading(false)
    }
  }

  const applyFilters = () => {
    let filtered = [...interfaces]

    // Filter by keyword
    if (searchKeyword) {
      const keyword = searchKeyword.toLowerCase()
      filtered = filtered.filter(
        (iface) =>
          iface.displayName?.toLowerCase().includes(keyword) ||
          iface.description?.toLowerCase().includes(keyword) ||
          iface.dtmi?.toLowerCase().includes(keyword)
      )
    }

    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = filtered.filter((iface) => iface.category === selectedCategory)
    }

    // Filter by domain
    if (selectedDomain !== 'all') {
      filtered = filtered.filter((iface) => {
        const tags = iface.tags || []
        return tags.includes(selectedDomain)
      })
    }

    setFilteredInterfaces(filtered)
  }

  const handleSelectInterface = async (iface) => {
    setSelectedInterface(iface)
    setLoadingSummary(true)
    try {
      const summary = await getInterfaceSummary(iface.dtmi)
      setInterfaceSummary(summary)
    } catch (err) {
      console.error('Failed to load interface summary:', err)
    } finally {
      setLoadingSummary(false)
    }
  }

  const handleConfirmSelection = () => {
    if (selectedInterface) {
      onSelect(selectedInterface, interfaceSummary)
      handleClose()
    }
  }

  const handleClose = () => {
    setSelectedInterface(null)
    setInterfaceSummary(null)
    setSearchKeyword('')
    setSelectedCategory('all')
    setSelectedDomain(domain || 'all')
    onClose()
  }

  // Extract unique categories and domains
  const categories = ['all', ...new Set(interfaces.map((i) => i.category).filter(Boolean))]
  // Use category as domain (more reliable than tags)
  const domains = [
    'all',
    ...new Set(interfaces.map((i) => i.category).filter((cat) => cat && cat !== 'base'))
  ]

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-900 rounded-lg shadow-xl w-full max-w-5xl max-h-[90vh] flex flex-col border border-transparent dark:border-slate-700">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-slate-700">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-slate-100">
              {t('dtdl.selectInterface')}
            </h2>
            <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
              {t('dtdl.selectInterfaceDescription')}
            </p>
          </div>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 dark:text-slate-500 dark:hover:text-slate-200 transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Filters */}
        <div className="p-6 border-b border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 dark:text-slate-500" size={20} />
              <input
                type="text"
                placeholder={t('dtdl.searchPlaceholder')}
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-gray-900 dark:text-slate-100 placeholder:text-gray-400 dark:placeholder:text-slate-500 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Category Filter */}
            <div>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-gray-900 dark:text-slate-100 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat === 'all' ? t('dtdl.allCategories') : cat}
                  </option>
                ))}
              </select>
            </div>

            {/* Domain Filter */}
            <div>
              <select
                value={selectedDomain}
                onChange={(e) => setSelectedDomain(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-gray-900 dark:text-slate-100 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {domains.map((dom) => (
                  <option key={dom} value={dom}>
                    {dom === 'all' ? t('dtdl.allDomains') : dom}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Results count */}
          <div className="mt-3 text-sm text-gray-600 dark:text-slate-400">
            {t('dtdl.showingResults', { count: filteredInterfaces.length, total: interfaces.length })}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {/* Interface List */}
          <div className="w-1/2 border-r border-gray-200 dark:border-slate-700 overflow-y-auto bg-white dark:bg-slate-900">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 dark:border-blue-400"></div>
              </div>
            ) : error ? (
              <div className="p-6 text-center text-red-600 dark:text-red-400">
                {error}
              </div>
            ) : filteredInterfaces.length === 0 ? (
              <div className="p-6 text-center text-gray-500 dark:text-slate-400">
                {t('dtdl.noInterfacesFound')}
              </div>
            ) : (
              <div className="divide-y divide-gray-200 dark:divide-slate-700">
                {filteredInterfaces.map((iface) => (
                  <div
                    key={iface.dtmi}
                    onClick={() => handleSelectInterface(iface)}
                    className={`p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors ${
                      selectedInterface?.dtmi === iface.dtmi
                        ? 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-600 dark:border-blue-400'
                        : ''
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-medium text-gray-900 dark:text-slate-100">{iface.displayName}</h3>
                        <p className="text-xs text-gray-500 dark:text-slate-400 mt-1 font-mono">{iface.dtmi}</p>
                        <p className="text-sm text-gray-600 dark:text-slate-300 mt-2 line-clamp-2">{iface.description}</p>
                        <div className="flex flex-wrap gap-2 mt-2">
                          <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 dark:bg-slate-700 text-gray-800 dark:text-slate-200">
                            {iface.category}
                          </span>
                          {iface.tags?.slice(0, 3).map((tag) => (
                            <span key={tag} className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-200">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                      {selectedInterface?.dtmi === iface.dtmi && (
                        <CheckCircle className="text-blue-600 dark:text-blue-400 ml-2 flex-shrink-0" size={20} />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Interface Details */}
          <div className="w-1/2 overflow-y-auto bg-gray-50 dark:bg-slate-800/40">
            {!selectedInterface ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-400 dark:text-slate-500">
                <Info size={48} />
                <p className="mt-4 text-sm">{t('dtdl.selectInterfaceToView')}</p>
              </div>
            ) : loadingSummary ? (
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 dark:border-blue-400"></div>
              </div>
            ) : (
              <div className="p-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-slate-100 mb-2">
                  {selectedInterface.displayName}
                </h3>
                <p className="text-xs text-gray-500 dark:text-slate-400 mb-4 font-mono">{selectedInterface.dtmi}</p>
                <p className="text-sm text-gray-700 dark:text-slate-300 mb-6">{selectedInterface.description}</p>

                {interfaceSummary && (
                  <>
                    {/* Extends */}
                    {interfaceSummary.extends && (
                      <div className="mb-6">
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-slate-100 mb-2">{t('dtdl.extends')}</h4>
                        <p className="text-xs text-gray-600 dark:text-slate-300 font-mono bg-white dark:bg-slate-900 p-2 rounded border border-gray-200 dark:border-slate-700">
                          {interfaceSummary.extends}
                        </p>
                      </div>
                    )}

                    {/* Contents Summary */}
                    <div className="mb-6">
                      <h4 className="text-sm font-semibold text-gray-900 dark:text-slate-100 mb-2">{t('dtdl.contents')}</h4>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-white dark:bg-slate-900 p-3 rounded border border-gray-200 dark:border-slate-700">
                          <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{interfaceSummary.telemetryCount}</div>
                          <div className="text-xs text-gray-600 dark:text-slate-400">{t('dtdl.telemetry')}</div>
                        </div>
                        <div className="bg-white dark:bg-slate-900 p-3 rounded border border-gray-200 dark:border-slate-700">
                          <div className="text-2xl font-bold text-green-600 dark:text-green-400">{interfaceSummary.propertyCount}</div>
                          <div className="text-xs text-gray-600 dark:text-slate-400">{t('dtdl.properties')}</div>
                        </div>
                        <div className="bg-white dark:bg-slate-900 p-3 rounded border border-gray-200 dark:border-slate-700">
                          <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">{interfaceSummary.commandCount}</div>
                          <div className="text-xs text-gray-600 dark:text-slate-400">{t('dtdl.commands')}</div>
                        </div>
                        <div className="bg-white dark:bg-slate-900 p-3 rounded border border-gray-200 dark:border-slate-700">
                          <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">{interfaceSummary.componentCount}</div>
                          <div className="text-xs text-gray-600 dark:text-slate-400">{t('dtdl.components')}</div>
                        </div>
                      </div>
                    </div>

                    {/* Telemetry Details */}
                    {interfaceSummary.telemetryDetails?.length > 0 && (
                      <div className="mb-6">
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-slate-100 mb-3">Telemetry Details</h4>
                        <div className="space-y-2">
                          {interfaceSummary.telemetryDetails.map((tel) => (
                            <div key={tel.name} className="bg-white dark:bg-slate-900 p-3 rounded border border-gray-200 dark:border-slate-700">
                              <div className="flex items-start justify-between mb-1">
                                <div>
                                  <code className="text-sm font-medium text-blue-600 dark:text-blue-400">{tel.name}</code>
                                  <span className="text-xs text-gray-500 dark:text-slate-400 ml-2">({tel.type})</span>
                                </div>
                              </div>
                              {tel.description && (
                                <p className="text-xs text-gray-600 dark:text-slate-300 mb-1">{tel.description}</p>
                              )}
                              {tel.unit && (
                                <span className="text-xs text-gray-500 dark:text-slate-400">Unit: {tel.unit}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Property Details */}
                    {interfaceSummary.propertyDetails?.length > 0 && (
                      <div className="mb-6">
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-slate-100 mb-3">Property Details</h4>
                        <div className="space-y-2">
                          {interfaceSummary.propertyDetails.map((prop) => (
                            <div key={prop.name} className="bg-white dark:bg-slate-900 p-3 rounded border border-gray-200 dark:border-slate-700">
                              <div className="flex items-start justify-between mb-1">
                                <div>
                                  <code className="text-sm font-medium text-green-600 dark:text-green-400">{prop.name}</code>
                                  <span className="text-xs text-gray-500 dark:text-slate-400 ml-2">({prop.type})</span>
                                </div>
                                {prop.writable !== undefined && (
                                  <span className={`text-xs px-2 py-0.5 rounded ${prop.writable ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-200' : 'bg-gray-100 dark:bg-slate-700 text-gray-800 dark:text-slate-200'}`}>
                                    {prop.writable ? "Writable" : "Read-only"}
                                  </span>
                                )}
                              </div>
                              {prop.description && (
                                <p className="text-xs text-gray-600 dark:text-slate-300 mb-1">{prop.description}</p>
                              )}
                              {prop.unit && (
                                <span className="text-xs text-gray-500 dark:text-slate-400">Unit: {prop.unit}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Component List */}
                    {interfaceSummary.componentNames?.length > 0 && (
                      <div className="mb-6">
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-slate-100 mb-2">{t('dtdl.componentFields')}</h4>
                        <ul className="space-y-1">
                          {interfaceSummary.componentNames.map((name) => (
                            <li key={name} className="text-sm text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-900 px-3 py-2 rounded border border-gray-200 dark:border-slate-700">
                              <code className="text-orange-600 dark:text-orange-400">{name}</code>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50">
          <div className="text-sm text-gray-600 dark:text-slate-300">
            {selectedInterface ? (
              <span>
                {t('dtdl.selected')}: <strong className="text-gray-900 dark:text-slate-100">{selectedInterface.displayName}</strong>
              </span>
            ) : (
              <span>{t('dtdl.noInterfaceSelected')}</span>
            )}
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleClose}
              className="px-4 py-2 border border-gray-300 dark:border-slate-700 rounded-md text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-900 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors"
            >
              {t('common.cancel')}
            </button>
            <button
              onClick={handleConfirmSelection}
              disabled={!selectedInterface}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:bg-gray-300 dark:disabled:bg-slate-700 disabled:text-gray-500 dark:disabled:text-slate-400 disabled:cursor-not-allowed"
            >
              {t('common.select')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DTDLSelectionModal
