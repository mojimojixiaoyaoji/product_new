import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type ThemeMode = 'dark' | 'light' | 'system'

const THEME_STORAGE_KEY = 'admin_templates_theme'
const THEME_MODE_STORAGE_KEY = 'admin_templates_theme_mode'

export const useThemeStore = defineStore('theme', () => {
  // Get initial theme from localStorage or default to system
  const savedMode = localStorage.getItem(THEME_MODE_STORAGE_KEY) as ThemeMode | null
  const mode = ref<ThemeMode>(savedMode || 'system')

  // Determine actual theme based on mode
  const getSystemTheme = (): 'dark' | 'light' => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    return 'dark'
  }

  const savedTheme = localStorage.getItem(THEME_STORAGE_KEY) as 'dark' | 'light' | null
  const theme = ref<'dark' | 'light'>(savedTheme || getSystemTheme())

  // Apply theme to document
  const applyTheme = (newTheme: 'dark' | 'light') => {
    theme.value = newTheme
    localStorage.setItem(THEME_STORAGE_KEY, newTheme)
    document.documentElement.setAttribute('data-theme', newTheme)
  }

  // Update theme based on current mode
  const updateTheme = () => {
    if (mode.value === 'system') {
      applyTheme(getSystemTheme())
    } else {
      applyTheme(mode.value)
    }
  }

  // Watch for mode changes
  watch(mode, (newMode) => {
    localStorage.setItem(THEME_MODE_STORAGE_KEY, newMode)
    updateTheme()
  })

  // Listen for system theme changes when in system mode
  if (typeof window !== 'undefined' && window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (mode.value === 'system') {
        updateTheme()
      }
    })
  }

  // Set theme mode
  const setMode = (newMode: ThemeMode) => {
    mode.value = newMode
  }

  // Toggle between dark and light
  const toggleTheme = () => {
    if (mode.value === 'system') {
      // If system, switch to the opposite of current
      setMode(theme.value === 'dark' ? 'light' : 'dark')
    } else {
      setMode(mode.value === 'dark' ? 'light' : 'dark')
    }
  }

  // Initialize theme on first load
  updateTheme()

  return {
    mode,
    theme,
    setMode,
    toggleTheme,
    updateTheme
  }
})
