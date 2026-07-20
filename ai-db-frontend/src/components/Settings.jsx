function Settings({
  settings,
  setSettings,
}) {

  return (
    <div className="settings-section">

      <h4>⚙ Settings</h4>

      <div className="setting-item">
        <label>
          <input
            type="checkbox"
            checked={settings.darkMode}
            onChange={() =>
              setSettings(prev => ({
                ...prev,
                darkMode:
                  !prev.darkMode
              }))
            }
          />
          Dark Mode
        </label>
      </div>

      <div className="setting-item">
        <label>
          <input
            type="checkbox"
            checked={settings.showCharts}
            onChange={() =>
              setSettings(prev => ({
                ...prev,
                showCharts:
                  !prev.showCharts
              }))
            }
          />
          Show Charts
        </label>
      </div>

      <div className="setting-item">
        <label>
          <input
            type="checkbox"
            checked={settings.showInsights}
            onChange={() =>
              setSettings(prev => ({
                ...prev,
                showInsights:
                  !prev.showInsights
              }))
            }
          />
          Show AI Insights
        </label>
      </div>

      <div className="setting-item">
        <label>
          <input
            type="checkbox"
            checked={settings.autoConnect}
            onChange={() =>
              setSettings(prev => ({
                ...prev,
                autoConnect:
                  !prev.autoConnect
              }))
            }
          />
          Auto Connect Last Database
        </label>
      </div>

    </div>
  );
}

export default Settings;