import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import { ThemeProvider } from '@/components/theme-provider'
import Layout from '@/components/layout/Layout'
import CreateTwinScaleThing from '@/pages/twinscale/CreateTwinScaleThing'
import TwinScaleThingList from '@/pages/twinscale/TwinScaleThingList'
import TwinScaleThingDetails from '@/pages/twinscale/TwinScaleThingDetails'
import SearchThings from '@/pages/twinscale/SearchThings'

function App() {
  return (
    <ThemeProvider defaultTheme="light" storageKey="twinscale-lite-theme">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/things" replace />} />
            
            {/* TwinScale Thing Routes */}
            <Route path="things" element={<TwinScaleThingList />} />
            <Route path="things/create" element={<CreateTwinScaleThing />} />
            <Route path="things/search" element={<SearchThings />} />
            <Route path="things/:interfaceName" element={<TwinScaleThingDetails />} />
            
            {/* 404 */}
            <Route path="*" element={
              <div className="flex items-center justify-center min-h-screen">
                <div className="text-center">
                  <h1 className="text-2xl font-bold mb-4">Page Not Found</h1>
                  <p className="text-muted-foreground mb-4">The page you are looking for does not exist.</p>
                  <Navigate to="/things" replace />
                </div>
              </div>
            } />
          </Route>
        </Routes>
        <Toaster />
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App

