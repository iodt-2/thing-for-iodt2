import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import { ThemeProvider } from '@/components/theme-provider'
import Layout from '@/components/layout/Layout'
import CreateTwinThing from '@/pages/twin/CreateTwinThing'
import TwinThingList from '@/pages/twin/TwinThingList'
import TwinThingDetails from '@/pages/twin/TwinThingDetails'
import SearchThings from '@/pages/twin/SearchThings'
import TwinGraphView from '@/pages/twin/TwinGraphView'

function App() {
  return (
    <ThemeProvider defaultTheme="light" storageKey="twin-lite-theme">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/things" replace />} />
            
            {/* Twin Thing Routes */}
            <Route path="things" element={<TwinThingList />} />
            <Route path="things/create" element={<CreateTwinThing />} />
            <Route path="things/search" element={<SearchThings />} />
            <Route path="things/graph" element={<TwinGraphView />} />
            <Route path="things/:interfaceName" element={<TwinThingDetails />} />
            
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

