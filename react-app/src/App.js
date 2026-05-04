import './App.css';
import { useEffect, useState } from 'react';

function App() {
  const [droneData, setDroneData] = useState({});
  const [selectedDroneId, setSelectedDroneId] = useState('all');
  const commandOptions = [
    'request_assign',
    'start_delivery',
    'return_signal',
    'unassign_signal',
    'drone_recovered',
    'recharge',
  ];

  useEffect(() => {
    const eventSource = new EventSource('http://brick.local:8080/sse');

    eventSource.addEventListener('telemetry', (event) => {
      const data = JSON.parse(event.data);
      const timestamp = new Date().toISOString();

      setDroneData((previousDroneData) => {
        const nextDroneData = { ...previousDroneData };

        Object.entries(data).forEach(([droneId, telemetry]) => {
          nextDroneData[droneId] = {
            ...(previousDroneData[droneId] || {}),
            ...telemetry,
            timestamp,
          };
        });

        return nextDroneData;
      });
    });

    eventSource.onerror = (event) => {
      console.error('SSE error:', event);
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const sendCommand = async (path, command) => {
    try {
      const response = await fetch(`http://brick.local:8080${path}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'text/plain',
        },
        body: command,
      });

      if (!response.ok) {
        throw new Error(`Command request failed with status ${response.status}`);
      }
    } catch (error) {
      console.error('Command request failed:', error);
    }
  };

  useEffect(() => {
    const cleanupInterval = setInterval(() => {
      const staleThresholdMs = 30000;
      const now = Date.now();

      setDroneData((previousDroneData) => {
        const nextDroneData = {};

        Object.entries(previousDroneData).forEach(([droneId, telemetry]) => {
          const lastUpdateMs = Date.parse(telemetry.timestamp || '');
          if (!Number.isNaN(lastUpdateMs) && now - lastUpdateMs <= staleThresholdMs) {
            nextDroneData[droneId] = telemetry;
          }
        });

        return nextDroneData;
      });
    }, 5000);

    return () => {
      clearInterval(cleanupInterval);
    };
  }, []);

  useEffect(() => {
    if (selectedDroneId !== 'all' && !droneData[selectedDroneId]) {
      setSelectedDroneId('all');
    }
  }, [droneData, selectedDroneId]);

  const droneIds = Object.keys(droneData).sort();
  const visibleDrones = selectedDroneId === 'all' ? droneIds : [selectedDroneId];

  const formatNumber = (value, decimals = 2) => {
    const numericValue = Number(value);
    if (Number.isNaN(numericValue)) {
      return '-';
    }
    return numericValue.toFixed(decimals);
  };

  const renderDroneCard = (droneId) => {
    const telemetry = droneData[droneId];
    if (!telemetry) {
      return null;
    }

    const batteryValue = Math.max(0, Math.min(100, Number(telemetry.battery) || 0));
    const telemetryActive = telemetry.telemetry === 'active';
    const stateLabel = telemetry.state || 'unknown';
    const target = telemetry.target;

    let batteryClass = 'battery-fill battery-good';
    if (batteryValue < 30) {
      batteryClass = 'battery-fill battery-critical';
    } else if (batteryValue < 60) {
      batteryClass = 'battery-fill battery-warning';
    }

    return (
      <article key={droneId} className="drone-card">
        <div className="drone-card-header">
          <h2>{droneId}</h2>
          <span className="state-pill">{stateLabel}</span>
        </div>

        <div className="metric-row">
          <span>Telemetry</span>
          <span className={telemetryActive ? 'status-dot status-active' : 'status-dot status-inactive'}>
            {telemetry.telemetry || 'inactive'}
          </span>
        </div>

        <div className="metric-row">
          <span>Battery</span>
          <strong>{formatNumber(batteryValue, 1)}%</strong>
        </div>
        <div className="battery-track">
          <div className={batteryClass} style={{ width: `${batteryValue}%` }} />
        </div>

        <div className="metric-grid">
          <div className="metric-tile">
            <span className="metric-label">Altitude</span>
            <strong>{formatNumber(telemetry.altitude)} m</strong>
          </div>
          <div className="metric-tile">
            <span className="metric-label">Pressure</span>
            <strong>{formatNumber(telemetry.pressure)} hPa</strong>
          </div>
          <div className="metric-tile">
            <span className="metric-label">Phase</span>
            <strong>{telemetry.phase || '-'}</strong>
          </div>
          <div className="metric-tile">
            <span className="metric-label">Last Update</span>
            <strong>{new Date(telemetry.timestamp).toLocaleTimeString()}</strong>
          </div>
        </div>

        <div className="target-box">
          <span className="metric-label">Target</span>
          {target ? (
            <div>
              <div>NorthSouth: {formatNumber(target.NorthSouth, 4)}</div>
              <div>EastWest: {formatNumber(target.EastWest, 4)}</div>
            </div>
          ) : (
            <div>No target assigned</div>
          )}
        </div>
      </article>
    );
  };

  const isSpecificDroneSelected = selectedDroneId !== 'all' && Boolean(droneData[selectedDroneId]);

  return (
    <div className="App">
      <header className="App-header">
        <div className="dashboard-header">
          <h1>Drone Telemetry Dashboard</h1>
          <p>Tracked drones: {droneIds.length}</p>
        </div>

        <div className="controls-row">
          <div className="selection-group">
            <label htmlFor="drone-filter">Show drone</label>
            <select
              id="drone-filter"
              value={selectedDroneId}
              onChange={(event) => setSelectedDroneId(event.target.value)}
            >
              <option value="all">All drones</option>
              {droneIds.map((droneId) => (
                <option key={droneId} value={droneId}>
                  {droneId}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            className="command-button scan-button"
            onClick={() => sendCommand('/commands/all', 'send_telemetry')}
          >
            Scan
          </button>
        </div>

        {isSpecificDroneSelected ? (
          <section className="command-panel">
            <div className="command-panel-header">
              <h2>Commands for {selectedDroneId}</h2>
              <p>These send POST requests to /commands/{selectedDroneId}</p>
            </div>

            <div className="command-grid">
              {commandOptions.map((command) => (
                <button
                  key={command}
                  type="button"
                  className="command-button"
                  onClick={() => sendCommand(`/commands/${selectedDroneId}`, command)}
                >
                  {command}
                </button>
              ))}
            </div>
          </section>
        ) : null}

        <section className="drone-grid">
          {visibleDrones.length > 0 ? (
            visibleDrones.map((droneId) => renderDroneCard(droneId)).filter(Boolean)
          ) : (
            <p className="empty-state">No telemetry available for this selection.</p>
          )}
        </section>
      </header>
    </div>
  );
}

export default App;
