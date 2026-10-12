import { useEffect } from 'react'
import GlobeScene from './components/GlobeScene'
import DataPanel from './components/DataPanel'
import Legend from './components/Legend'
import TopNav from './components/TopNav'
import Login from './components/auth/Login'
import AgentBar from './components/AgentBar'
import { useGeoStore, useAuthStore } from './store'
import './App.css'

export default function App() {
  const { isLoggedIn, init } = useAuthStore()
  const {
    loadPoints, loadArcs, loadGlobeCountries,
    loadAwsRegions, loadAzureRegions,
    loadGcpRegions, loadAlibabaRegions, loadOciRegions, loadIbmRegions,
  } = useGeoStore()

  useEffect(() => {
    init()
  }, [])

  useEffect(() => {
    if (!isLoggedIn) return
    loadPoints()
    loadArcs()
    loadGlobeCountries()
    loadAwsRegions()
    loadAzureRegions()
    loadGcpRegions()
    loadAlibabaRegions()
    loadOciRegions()
    loadIbmRegions()
  }, [isLoggedIn])

  if (!isLoggedIn) return <Login />

  return (
    <div className="app">
      <div className="globe-canvas">
        <GlobeScene />
      </div>

      <div className="vignette" />

      <TopNav />

      <Legend />
      <DataPanel />

      <AgentBar />
    </div>
  )
}
