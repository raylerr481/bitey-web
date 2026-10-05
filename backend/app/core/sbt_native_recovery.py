from __future__ import annotations

import re


def answer_from_sbt_evidence(evidence: str) -> str:
    evidence = str(evidence or "")
    if "SBT Turtle Controller verified from MT4 live snapshot." in evidence:
        fields: dict[str, str] = {}
        for key in ("Symbol", "timeframe", "signal", "next_action", "position_count", "risk_pct", "drawdown_pct", "learning_status", "proposal_pending"):
            match = re.search(rf"{re.escape(key)}:\s*([^;]+)", evidence, re.I)
            if match:
                fields[key.lower()] = match.group(1).strip()
        return (
            "El Turtle está conectado a SBT y su estado fue verificado desde una captura viva de MT4.\n\n"
            f"Símbolo: {fields.get('symbol', '—')} · Timeframe: {fields.get('timeframe', '—')}\n"
            f"Señal: {fields.get('signal', 'NONE')} · Próxima acción: {fields.get('next_action', 'WAIT')}\n"
            f"Posiciones: {fields.get('position_count', '0')} · Riesgo: {fields.get('risk_pct', '0')}% · Drawdown: {fields.get('drawdown_pct', '0')}%\n"
            f"Aprendizaje: {fields.get('learning_status', 'OBSERVING')} · Propuesta pendiente: {fields.get('proposal_pending', 'False')}\n\n"
            "El Risk Gate de SBT mantiene la autoridad de ejecución y el cambio de parámetros en vivo no es automático."
        )
    if "SBT Turtle Controller is reachable, but it has no current MT4 live snapshot." in evidence:
        return "El Turtle Controller de SBT está accesible, pero no tiene una captura viva actual de MT4. Por eso no puedo afirmar qué señal, posición o resultado tiene ahora mismo."
    if "Bitey IA could not reach SBT Turtle Controller." in evidence:
        return "No pude consultar el Turtle Controller de SBT en este momento. No voy a inventar su estado, señal, posición ni resultado."
    if "SBT AI Bot Lab verified from MT4 context." in evidence:
        values = {}
        for key in ("Bot", "strategy", "symbol", "timeframe", "mode"):
            match = re.search(rf"{re.escape(key)}:\s*([^;]+)", evidence, re.I)
            if match:
                values[key.lower()] = match.group(1).strip()
        return (
            "El AI Bot Lab de SBT está conectado a un contexto real de MT4.\n\n"
            f"Bot: {values.get('bot', '—')} · Estrategia: {values.get('strategy', '—')}\n"
            f"Mercado: {values.get('symbol', '—')} {values.get('timeframe', '—')} · Modo: {values.get('mode', '—')}\n\n"
            "La mejora puede proponer y validar cambios mediante evidencia, pero no aplica automáticamente parámetros al EA activo."
        )
    if "SBT AI Bot Lab is reachable, but no MT4 bot snapshot is currently connected." in evidence:
        return "El AI Bot Lab de SBT está accesible, pero no hay una captura actual de MT4 conectada. No puedo afirmar qué bot está activo ni qué está optimizando."
    if "Bitey IA could not reach SBT AI Bot Lab." in evidence:
        return "No pude conectar con el AI Bot Lab de SBT en este momento. No voy a inventar qué bot está activo ni qué está optimizando."
    return ""
