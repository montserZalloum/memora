import './App.css'
import { useState } from 'react'
import { LessonMap } from './pages/LessonMap'
import { GameSession } from './pages/GameSession'

function App() {
  const [currentView, setCurrentView] = useState<'map' | 'game'>('map')
  const [selectedLessonId, setSelectedLessonId] = useState<string | null>(null)

  const handleLessonSelect = (lessonId: string) => {
    setSelectedLessonId(lessonId)
    setCurrentView('game')
  }

  const handleBackToMap = () => {
    setCurrentView('map')
    setSelectedLessonId(null)
  }

  if (currentView === 'game' && selectedLessonId) {
    return <GameSession lessonId={selectedLessonId} onExit={handleBackToMap} />
  }

  return <LessonMap onLessonSelect={handleLessonSelect} />
}

export default App
