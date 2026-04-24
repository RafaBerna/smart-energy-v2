import { useState } from "react";
import { styles } from "./styles";
import Home from "./screens/Home";
import Prices from "./screens/prices";

// ======================
// COMPONENTS · PLACEHOLDER
// ======================

function Consumption() {
  return (
    <div style={styles.page}>
      <div style={styles.phone}>
        <div style={styles.loadingCard}>Pantalla de consumo</div>
      </div>
    </div>
  );
}

function Utilities() {
  return (
    <div style={styles.page}>
      <div style={styles.phone}>
        <div style={styles.loadingCard}>Pantalla de utilidades</div>
      </div>
    </div>
  );
}

// ======================
// COMPONENT · APP
// ======================

function App() {
  // ======================
  // STATE
  // ======================

  const [activeTab, setActiveTab] = useState("inicio");

  // ======================
  // RENDER · MAIN
  // ======================

  return (
    <div style={styles.appShell}>
      {/* ======================
          SCREEN CONTENT
      ====================== */}
      <div style={styles.screenContent}>
        <div style={{ display: activeTab === "inicio" ? "block" : "none" }}>
          <Home />
        </div>

        <div style={{ display: activeTab === "precios" ? "block" : "none" }}>
          <Prices />
        </div>

        <div style={{ display: activeTab === "consumo" ? "block" : "none" }}>
          <Consumption />
        </div>

        <div style={{ display: activeTab === "utilidades" ? "block" : "none" }}>
          <Utilities />
        </div>
      </div>

      {/* ======================
          NAVIGATION
      ====================== */}
      <nav style={styles.bottomNav}>
        <button
          style={styles.getNavItemStyle(activeTab === "inicio")}
          onClick={() => setActiveTab("inicio")}
        >
          Inicio
        </button>

        <button
          style={styles.getNavItemStyle(activeTab === "precios")}
          onClick={() => setActiveTab("precios")}
        >
          Precios
        </button>

        <button
          style={styles.getNavItemStyle(activeTab === "consumo")}
          onClick={() => setActiveTab("consumo")}
        >
          Consumo
        </button>

        <button
          style={styles.getNavItemStyle(activeTab === "utilidades")}
          onClick={() => setActiveTab("utilidades")}
        >
          Utilidades
        </button>
      </nav>
    </div>
  );
}

export default App;