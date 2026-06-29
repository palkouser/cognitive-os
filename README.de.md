
![LightAgent Banner](docs/images/lightagent-banner.jpg)
<div align="center">
  <p>
    <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License"></a>
    <a href="https://github.com/wanxingai/LightAgent/releases"><img src="https://img.shields.io/github/release/wanxingai/LightAgent.svg" alt="GitHub release"></a>
    <a href="https://github.com/wanxingai/LightAgent/issues"><img src="https://img.shields.io/github/issues/wanxingai/LightAgent.svg" alt="GitHub issues"></a>
    <a href="https://github.com/wanxingai/LightAgent/stargazers"><img src="https://img.shields.io/github/stars/wanxingai/LightAgent.svg" alt="GitHub stars"></a>
    <a href="https://github.com/wanxingai/LightAgent/network"><img src="https://img.shields.io/github/forks/wanxingai/LightAgent.svg" alt="GitHub forks"></a>
    <a href="https://github.com/wanxingai/LightAgent/graphs/contributors"><img src="https://img.shields.io/github/contributors/wanxingai/LightAgent.svg" alt="GitHub contributors"></a>
    <a href="https://sufe-aiflm-lab.github.io/LightAgent/"><img src="https://img.shields.io/badge/docs-latest-brightgreen.svg" alt="Docs"></a>
    <a href="https://pypi.org/project/lightagent/"><img src="https://img.shields.io/pypi/v/lightagent.svg" alt="PyPI"></a>
    <a href="https://pypi.org/project/lightagent/"><img src="https://img.shields.io/pypi/dm/lightagent.svg" alt="Downloads"></a>
    <a href="https://pypi.org/project/lightagent/"><img src="https://img.shields.io/pypi/pyversions/lightagent.svg" alt="Python Version"></a>
    <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code Style"></a>
  </p>
</div>
<div align="center">
  <p>
    <a href="README.md">English</a> | 
    <a href="README.zh-CN.md">简体中文</a> | 
    <a href="README.zh-TW.md">繁體中文</a> | 
    <a href="README.es.md">Español</a> | 
    <a href="README.fr.md">Français</a> | 
    Deutsch | 
    <a href="README.ja.md">日本語</a> | 
    <a href="README.ko.md">한국어</a> | 
    <a href="README.pt.md">Português</a> | 
    <a href="README.ru.md">Русский</a> 
  </p>
</div>
<div align="center">
  <h1>LightAgent🚀（Nächste Generation des Agentic AI-Frameworks）</h1>
</div>

**LightAgent** ist ein extrem leichtgewichtiges, speicherfähiges (`mem0`), werkzeugbasiertes (`Tools`), denkbaumgestütztes (`ToT`) aktives Agenten-Framework, das vollständig Open Source ist. Es unterstützt eine einfachere Multi-Agenten-Kollaboration als OpenAI Swarm, ermöglicht es, in einem Schritt Agenten mit Selbstlernfähigkeiten zu erstellen, und unterstützt die Anbindung an das MCP-Protokoll über stdio und sse. Das zugrunde liegende Modell unterstützt OpenAI, Zhiyu ChatGLM, DeepSeek, Jieyue Xingchen, Qwen Tongyi Qianwen große Modelle usw. Gleichzeitig unterstützt LightAgent die Ausgabe von OpenAI Stream-Format-API-Diensten und ermöglicht eine nahtlose Integration in alle gängigen Chat-Frameworks. 🌟

---

## Neuigkeiten
- <img src="https://img.alicdn.com/imgextra/i3/O1CN01SFL0Gu26nrQBFKXFR_!!6000000007707-2-tps-500-500.png" alt="new" width="30" height="30"/>**[2026-06-24]** LightAgent v0.9.0: ergänzt persistente LightFlow-Checkpoints, Resume/Rerun, Freigabeknoten, klarere Schrittzustände, Trace-Metadaten, Guardrails-Vorlagen, MemoryPolicy-Kontrollen und den SharedMemoryPool-Prototyp.
- **[2026-06-14]** LightAgent v0.8.1: ergänzt MemoryScope-Konventionen und MemoryPolicy-Filter nach Herkunft, Umfang und Vertrauen.
- **[2026-06-02]** LightAgent v0.8.0: führt LightFlow für deterministische mehrstufige Workflows ein.

Ältere Hinweise finden Sie in den [GitHub Releases](https://github.com/wanxingai/LightAgent/releases).

---

## ✨ Eigenschaften

- **Leicht und effizient** 🚀: Minimalistisches Design, schnelle Bereitstellung, geeignet für verschiedene Anwendungsfälle. (Kein LangChain, Kein LlamaIndex) 100% Python-Implementierung, keine zusätzlichen Abhängigkeiten, der Kerncode umfasst nur 1000 Zeilen und ist vollständig Open Source. 
- **Speicherunterstützung** 🧠: Unterstützt benutzerdefinierte Langzeitgedächtnisse für jeden Benutzer, native Unterstützung des `mem0`-Speichermoduls, das die personalisierte Erinnerung des Benutzers während des Gesprächs automatisch verwaltet und den Agenten intelligenter macht.
- **Selbstlernen** 📚️: Jeder Agent hat die Fähigkeit zum selbstständigen Lernen, und berechtigte Administratoren können jeden Agenten verwalten.
- **Werkzeugintegration** 🛠️: Unterstützt benutzerdefinierte Werkzeuge (`Tools`), automatisierte Werkzeuggenerierung, flexible Erweiterung zur Erfüllung vielfältiger Anforderungen.  
- **Komplexe Ziele** 🌳: Integriertes, reflektierendes Denkbaum-Modul (ToT), das komplexe Aufgabenzerlegungen und mehrstufiges Denken unterstützt, um die Aufgabenbearbeitungsfähigkeit zu verbessern.  
- **Multi-Agenten-Kooperation** 🤖: Einfachere Implementierung der Multi-Agenten-Kooperation als Swarm, integrierte LightSwarm-Funktion zur Absichtserkennung und Aufgabenübertragung, die es ermöglicht, Benutzereingaben intelligenter zu verarbeiten und Aufgaben bei Bedarf an andere Agenten zu übertragen. 
- **Unabhängige Ausführung** 🤖: Selbstständige Durchführung von Aufgaben ohne menschliches Eingreifen.  
- **Unterstützung mehrerer Modelle** 🔄: Kompatibel mit OpenAI, Zhiyu ChatGLM, Baichuan große Modelle, StepFun, DeepSeek, Qwen-Serie große Modelle.  
- **Stream-API** 🌊: Unterstützt die Ausgabe von OpenAI Stream-Format-API-Diensten, nahtlose Integration in gängige Chat-Frameworks zur Verbesserung der Benutzererfahrung.  
- **Werkzeuggenerator** 🚀: Geben Sie einfach Ihre API-Dokumentation an den [Werkzeuggenerator] weiter, und er wird automatisch Ihre maßgeschneiderten Werkzeuge erstellen, sodass Sie in nur einer Stunde Hunderte von personalisierten benutzerdefinierten Werkzeugen schnell erstellen können, um die Effizienz zu steigern und Ihr kreatives Potenzial freizusetzen.
- **Selbstlernender Agent** 🧠️: Jeder Agent hat die Fähigkeit, seine eigene Szenarienerinnerung zu entwickeln und aus den Gesprächen mit Benutzern zu lernen.
- **Adaptive Werkzeugmechanismen** 🛠️: Unterstützung für die Hinzufügung unbegrenzter Werkzeuge, Auswahl von Kandidatenwerkzeugen aus Tausenden von Werkzeugen durch das große Modell, Filtern irrelevanter Werkzeuge und anschließende Einreichung des Kontexts an das große Modell, was den Token-Verbrauch erheblich senken kann.
- **Workflow-Orchestrierung** 🔁: LightFlow verkettet Agenten zu deterministischen Workflows mit expliziten Abhängigkeiten, Ausgabeübergabe, Wiederholungen, Checkpoints, Resume/Rerun, Freigaben, Fallback-Agenten und nachvollziehbarer Ausführung.
- **Shared-Memory-Prototyp** 🧠: SharedMemoryPool bietet gemeinsam genutzten In-Memory-Speicher mit Herkunftsmetadaten, bereichsbezogener Suche und MemoryPolicy-kompatiblen Ergebnissen.
- **Guardrails-Vorlagen** 🛡️: Wiederverwendbare Eingabe-, Werkzeug- und Ausgabe-Regeln blockieren private Daten, bestätigen sensible Tools, prüfen riskante Parameter und redigieren Ausgaben.
- **Runtime Hooks** 🧩: Geordnetes `hooks=[...]`-Middleware-System zum Beobachten, Ersetzen oder Blockieren von Run-, Modell-, Tool-, Memory- und LightFlow-Schrittphasen.

## 🧭 Architektur auf einen Blick

| Ebene | Haupt-API | Nutzen Sie sie für |
| --- | --- | --- |
| Einzel-Agent-Runtime | `LightAgent` | Einen Agenten mit Modell, Tools, Speicher, Streaming, Trace und Guardrails. |
| Multi-Agent-Routing | `LightSwarm` | Rollenbasierte Delegation zwischen spezialisierten Agenten. |
| Deterministischer Workflow | `LightFlow` | DAG, Wiederholungen, Checkpoints, Freigaben, Resume und Rerun. |
| Tools und Integrationen | `tools`, `ToolRegistry`, MCP | Python-Tools, generierte Tools, Runtime-Laden oder MCP-Server. |
| Speichergrenze | `MemoryPolicy`, `MemoryScope` | Tenant-Isolation, Herkunft, Vertrauen, Ablauf und Schreibzulassung. |
| Gemeinsamer Speicher | `SharedMemoryPool` | Experimente mit gemeinsamem Speicher zwischen Agenten. |
| Sicherheit | `input_guardrails`, `tool_guardrails`, `output_guardrails` | Datenschutz, Tool-Bestätigung, riskante Parameter und Ausgaberedaktion. |
| Runtime Hooks | `hooks`, `HookContext`, `HookDecision` | Policy, Audit, Redaktion, Routing und Payload-Mutation an Lifecycle-Grenzen. |
| Beobachtbarkeit | `trace=True`, `agent.export_trace()` | Strukturierte Run-, Modell-, Tool-, Fehler- und Workflow-Ereignisse. |

## Zentrale Nutzungsmuster

LightAgent hält den Standardaufruf einfach und erlaubt Produktionskontrollen schrittweise.

| Muster | Minimaler Aufruf | Hinweise |
| --- | --- | --- |
| Basisantwort | `agent.run(query)` | Gibt standardmäßig einen String zurück. |
| Streaming | `agent.run(query, stream=True)` | Gibt OpenAI-kompatible Chunks zurück. |
| Strukturiertes Ergebnis | `agent.run(query, result_format="object")` | Gibt Inhalt und Metadaten zurück. |
| Trace | `agent.run(query, trace=True)` | Zeichnet Ereignisse auf, ohne den Standard-String zu ändern. |
| Benutzerspeicher | `agent.run(query, user_id="alice")` | Nutzt konfigurierten Speicher und MemoryPolicy. |
| Tools | `LightAgent(..., tools=[fn])` | Funktionen sollten `tool_info` bereitstellen. |
| Guardrails | `LightAgent(..., input_guardrails=[...])` | Fügt Eingabe-, Tool- und Ausgabe-Policies hinzu. |
| Runtime Hooks | `LightAgent(..., hooks=[fn])` | Beobachtet, ersetzt oder blockiert Lifecycle-Payloads. |
| Workflow | `LightFlow().step(...).run(query)` | Für deterministische mehrstufige Ausführung. |

## 📋 Dokumentation

- Für Installation, Modelle, Tools, Speicher, MCP, Skills, Streaming und LightSwarm siehe [FAQ](docs/FAQ.md).
- Für deterministische Workflows, Checkpoints, Resume/Rerun, Freigaben, Fallback-Agenten und Schrittstatus siehe [LightFlow](docs/lightflow.md).
- Für eigene Tools, ToolRegistry, ToolLoader, AsyncToolDispatcher und MCP siehe [Tools Guide](docs/tools.md).
- Für gemeinsamen Langzeitspeicher oder Graphspeicher siehe [Memory Security Guidance](docs/memory_security.md).
- Für SharedMemoryPool siehe [SharedMemoryPool](docs/shared_memory_pool.md).
- Für Speicher-Schreibzulassung und Ablaufregeln siehe [Memory Admission And Mutation Controls](docs/memory_admission.md).
- Für Eingabe-, Werkzeug- und Ausgabesicherheit siehe [Guardrails](docs/guardrails.md).
- Für Runtime-Middleware zum Beobachten, Ersetzen oder Blockieren von Payloads siehe [Runtime Hooks](docs/runtime_hooks.md).
- Für OpenRouter, lokale Modelle und OpenAI-kompatible Anbieter siehe [Model Provider Configuration](docs/model_providers.md).
- Für strukturierte Traces siehe [Trace Observability](docs/tracing.md).

## 🚧 Bald verfügbar

- **Agent-Kooperation Kommunikation** 🛠️: Agenten können Informationen austauschen und Nachrichten übermitteln, um komplexe Informationskommunikation und Aufgabenkoordination zu realisieren.
- **Agentenbewertung** 📊: Integriertes Agentenbewertungstool zur einfachen Bewertung und Optimierung Ihrer erstellten Agenten, um sie an Geschäftsszenarien anzupassen und das Intelligenzniveau kontinuierlich zu verbessern.  


## 🌟 Warum LightAgent wählen?

- **Open Source und kostenlos** 💖: Vollständig Open Source, gemeinschaftsgetrieben, kontinuierliche Updates, Beiträge sind willkommen!  
- **Einfach zu bedienen** 🎯: Ausführliche Dokumentation, reichhaltige Beispiele, schnelle Einarbeitung, einfache Integration in Ihr Projekt.  
- **Gemeinschaftsunterstützung** 👥: Aktive Entwicklergemeinschaft, die Ihnen jederzeit Hilfe und Antworten bietet.  
- **Hohe Leistung** ⚡: Optimiertes Design, effiziente Ausführung, erfüllt die Anforderungen an hochgradige Parallelität.  

---

## 🛠️ Schnellstart

### Installation der neuesten Version von LightAgent

```bash
pip install lightagent
```

(Optional) Installieren Sie das Mem0-Paket über pip:

```bash
pip install mem0ai
```

Oder Sie können Mem0 mit einem Klick auf einer Hosting-Plattform verwenden, [klicken Sie hier](https://www.mem0.ai/).


### Hello World Beispielcode

```python
from LightAgent import LightAgent

# Initialisieren des Agenten
agent = LightAgent(model="gpt-4o-mini", api_key="your_api_key", base_url= "your_base_url")

# Ausführen des Agenten
response = agent.run("Hallo, wer bist du?")
print(response)
```

### Einen Run-Trace prüfen (v0.7.0)

Tracing ist optional und hält das Standardverhalten von `agent.run()` kompatibel.

```python
from LightAgent import LightAgent

agent = LightAgent(model="gpt-4.1", api_key="your_api_key", base_url="your_base_url")

result = agent.run("Hello, who are you?", result_format="object", trace=True)
print(result.content)
print(result.trace_id)
print(result.trace)

for event in agent.export_trace():
    print(event["type"], event["data"])
```

### Einen LightFlow-Run checkpointen (v0.9.0)

`LightFlow` kann Workflow-Checkpoints speichern und fehlgeschlagene Runs fortsetzen, ohne beim ersten Schritt neu zu starten.

```python
from LightAgent import JsonLightFlowStore, LightAgent, LightFlow

research_agent = LightAgent(model="gpt-4.1", api_key="your_api_key", base_url="your_base_url")
writer_agent = LightAgent(model="gpt-4.1", api_key="your_api_key", base_url="your_base_url")

store = JsonLightFlowStore(".lightflow_runs")
flow = (
    LightFlow(store=store)
    .step("research", agent=research_agent, timeout=30)
    .step("write", agent=writer_agent, depends_on=["research"], max_retry=2)
)

result = flow.run("Analyze this company", run_id="report-001", trace=True)

if not result.success:
    result = flow.resume("report-001")

print(result.status)
print(flow.get_run("report-001")["steps"])
```

### SharedMemoryPool verwenden (v0.9.0)

`SharedMemoryPool` ist ein leichter In-Memory-Prototyp für gemeinsame Multi-Agent-Speicherexperimente.

```python
from LightAgent import LightAgent, MemoryPolicy, SharedMemoryPool

shared_memory = SharedMemoryPool(agent_name="writer")

agent = LightAgent(
    name="writer",
    model="gpt-4.1",
    api_key="your_api_key",
    base_url="your_base_url",
    memory=shared_memory,
    memory_policy=MemoryPolicy(
        namespace="tenant-a",
        allow_unattributed_results=False,
        allowed_sources=("user",),
        allowed_scopes=("user",),
    ),
)

agent.run("Remember that I prefer concise reports.", user_id="alice")
print(shared_memory.list_records(user_id="tenant-a:alice"))
```


### Festlegen des Selbstbewusstseins des Modells durch System-Prompt

```python
from LightAgent import LightAgent

# Initialisieren des Agenten
agent = LightAgent(
     role="Bitte erinnere dich, dass du LightAgent bist, ein nützlicher Assistent, der den Benutzern hilft, mehrere Werkzeuge zu verwenden.",  # Systemrollenbeschreibung
     model="deepseek-chat",  # Unterstützte Modelle: openai, chatglm, deepseek, qwen usw.
     api_key="your_api_key",  # Ersetzen Sie durch Ihren API-Schlüssel des großen Modells
     base_url="your_base_url",  # Ersetzen Sie durch die API-URL Ihres großen Modells
 )
# Ausführen des Agenten
response = agent.run("Darf ich fragen, wer du bist?")
print(response)
```

### Beispielcode zur Verwendung von Werkzeugen

```python
from LightAgent import LightAgent


# Definieren des Werkzeugs
def get_weather(city_name: str) -> str:
    """
    Holen Sie sich das aktuelle Wetter für `city_name`
    """
    return f"Suchergebnis: {city_name} Wetter ist klar"
# Definieren Sie die Werkzeuginformationen innerhalb der Funktion
get_weather.tool_info = {
    "tool_name": "get_weather",
    "tool_description": "Holen Sie sich die aktuellen Wetterinformationen für die angegebene Stadt",
    "tool_params": [
        {"name": "city_name", "description": "Der Name der Stadt, die abgefragt werden soll", "type": "string", "required": True},
    ]
}

tools = [get_weather]

# Initialisieren des Agenten
agent = LightAgent(model="qwen-turbo-2024-11-01", api_key="your_api_key", base_url= "your_base_url", tools=tools)

# Ausführen des Agenten
response = agent.run("Bitte helfen Sie mir, das Wetter in Shanghai zu überprüfen")
print(response)
```
Unterstützt die benutzerdefinierte Erstellung einer unbegrenzten Anzahl von Werkzeugen.

Beispiele für mehrere Werkzeuge: tools = [search_news,get_weather,get_stock_realtime_data,get_stock_kline_data]

---

## Funktionale Details

README enthält das zentrale Nutzungsmodell; längere Beispiele, Adapter-Setup und Produktionspraxis stehen in den Spezialdokumenten.

### 1. Abnehmbares Speichermodul (`mem0`)
LightAgent akzeptiert jedes Speicher-Backend mit `store(data, user_id)` und `retrieve(query, user_id)`. Verwenden Sie `user_id` zur Isolation und `MemoryPolicy` bei gemeinsamem Speicher.

### 2. Tool-Integration
Python-Funktionen mit `tool_info` stellen kontrollierte Fähigkeiten bereit. Für ToolRegistry, ToolLoader, AsyncToolDispatcher und MCP siehe [Tools Guide](docs/tools.md).

### 3. Tool-Generator
`agent.create_tool()` erzeugt Tool-Code aus API-Dokumentation oder natürlicher Sprache. Prüfen und testen Sie generierte Tools vor Produktion.

### 4. Denkbaum (ToT)
Aktivieren Sie `tree_of_thought=True` für Aufgaben mit expliziter Planung, Reflexion und Tool-Auswahl.

### 5. Multi-Agenten-Kooperation
`LightSwarm` delegiert Arbeit zwischen spezialisierten Agenten. Rollen sollten eng und Speicherzugriffe kontrolliert sein.

### 6. Streaming-API
`agent.run(query, stream=True)` gibt OpenAI-kompatible Chunks für Chat-UIs und lange Antworten zurück.

### 7. Selbstlernen des Agenten
Selbstlernen sollte mit `MemoryPolicy` kombiniert werden, um private, abgelaufene oder irrelevante Inhalte zu vermeiden.

### 8. Trace und Langfuse
LightAgent macht Ausführung über integrierte Traces oder Langfuse sichtbar.

### 9. Agentenbewertung
Agentenbewertung wird Verhalten anhand von Geschäftsszenarien messen.

### 10. LightFlow-Workflows
`LightFlow` ist die deterministische Workflow-Schicht für bekannte Ausführungsschritte.

- Schrittzustände: `pending`, `running`, `success`, `failed`, `skipped`, `waiting_approval`.
- DAG-Validierung: `flow.validate(strict=True)`.
- Schrittsteuerung: `timeout`, `max_retry`, `cancel_if`, `fallback_agent`, `requires_approval`, `approval_handler`.
- Persistenz und Wiederaufnahme: `JsonLightFlowStore`, `flow.resume(run_id)`, `flow.rerun_step(run_id, step_name)`, `flow.get_run(run_id)`, `flow.list_runs()`.

Siehe [LightFlow](docs/lightflow.md).

### 11. Guardrails
Guardrails sind leichte Hooks um Eingabe, Werkzeugaufrufe und Ausgabe.

```python
from LightAgent import (
    LightAgent,
    high_risk_parameter_guardrail,
    output_redaction_guardrail,
    privacy_input_guardrail,
    sensitive_tool_confirmation_guardrail,
)

agent = LightAgent(
    model="gpt-4.1",
    api_key="your_api_key",
    base_url="your_base_url",
    input_guardrails=[privacy_input_guardrail()],
    tool_guardrails=[
        sensitive_tool_confirmation_guardrail(["transfer_money"], approved=False),
        high_risk_parameter_guardrail({"amount": lambda value: float(value) <= 1000}),
    ],
    output_guardrails=[output_redaction_guardrail()],
)
```

Siehe [Guardrails](docs/guardrails.md).

### 12. SharedMemoryPool
`SharedMemoryPool` ist ein In-Memory-Prototyp für gemeinsamen Multi-Agent-Speicher und sollte mit `MemoryPolicy` genutzt werden.

## Unterstützung für gängige Agentenmodelle

LightAgent arbeitet mit OpenAI-kompatiblen Chat-Completion-Endpunkten: OpenAI, OpenRouter, Zhipu ChatGLM, DeepSeek, Qwen, StepFun, Moonshot/Kimi, MiniMax, vLLM, llama.cpp, Ollama und eigene Gateways.

For provider-specific parameters, base URLs, local model setup, and troubleshooting, see [Model Provider Configuration](docs/model_providers.md).

## Anwendungsszenarien

- **Intelligenter Kundenservice**: Bereitstellung effizienter Kundenunterstützung durch mehrstufige Dialoge und Werkzeugintegration.
- **Datenanalyse**: Verarbeitung komplexer Datenanalyseaufgaben mithilfe von Denkbaum und Multi-Agenten-Kooperation.
- **Automatisierte Werkzeuge**: Schnelles Erstellen maßgeschneiderter Werkzeuge durch automatisierte Werkzeuggenerierung.
- **Bildungsunterstützung**: Bereitstellung personalisierter Lernerfahrungen durch Gedächtnismodule und Stream-APIs.

---
 
## 🛠️ Beitragshinweise

Wir begrüßen alle Arten von Beiträgen! Egal ob Code, Dokumentation, Tests oder Feedback, alles ist eine große Hilfe für das Projekt. Wenn Sie gute Ideen haben oder einen Fehler finden, reichen Sie bitte ein Issue oder einen Pull Request ein. Hier sind die Schritte zur Mitwirkung:

1. **Forken Sie dieses Projekt**: Klicken Sie auf die Schaltfläche `Fork` in der oberen rechten Ecke, um das Projekt in Ihr GitHub-Repository zu kopieren.
2. **Erstellen Sie einen Branch**: Erstellen Sie lokal Ihren Entwicklungsbranch:  
   ```bash
   git checkout -b feature/YourFeature
   ```
3. **Änderungen einreichen**: Nach Abschluss der Entwicklung Ihre Änderungen einreichen:  
   ```bash
   git commit -m 'Fügen Sie eine Funktion hinzu'
   ```
4. **Branch pushen**: Pushen Sie den Branch in Ihr Remote-Repository:  
   ```bash
   git push origin feature/YourFeature
   ```
5. **Pull Request einreichen**: Reichen Sie einen Pull Request auf GitHub ein und beschreiben Sie Ihre Änderungen.

Wir werden Ihren Beitrag so schnell wie möglich überprüfen. Vielen Dank für Ihre Unterstützung!❤️

---

## 🙏 Danksagung

Die Entwicklung und Implementierung von LightAgent wäre ohne die Inspiration und Unterstützung folgender Open-Source-Projekte nicht möglich gewesen. Ein besonderer Dank geht an diese hervorragenden Projekte und Teams:

- **mem0**: Vielen Dank an [mem0](https://github.com/mem0ai/mem0) für das bereitgestellte Gedächtnismodul, das LightAgent eine starke Unterstützung für das Kontextmanagement bietet.  
- **Swarm**: Vielen Dank an [Swarm](https://github.com/openai/swarm) für die Designideen zur Multi-Agenten-Kooperation, die die Grundlage für die Multi-Agenten-Funktionalität von LightAgent bilden.  
- **ChatGLM3**: Vielen Dank an [ChatGLM3](https://github.com/THUDM/ChatGLM3) für die Unterstützung leistungsstarker chinesischer großer Modelle und die Designinspiration.  
- **Qwen**: Vielen Dank an [Qwen](https://github.com/QwenLM/Qwen) für die Unterstützung leistungsstarker chinesischer großer Modelle.  
- **DeepSeek-V3**: Vielen Dank an [DeepSeek-V3](https://github.com/deepseek-ai/DeepSeek-V3) für die Unterstützung leistungsstarker chinesischer großer Modelle.  
- **StepFun**: Vielen Dank an [step](https://www.stepfun.com/) für die Unterstützung leistungsstarker chinesischer großer Modelle.  

---

## 📄 Lizenz

LightAgent verwendet die [Apache 2.0 Lizenz](LICENSE). Sie können dieses Projekt frei verwenden, ändern und verteilen, müssen jedoch die Lizenzbedingungen einhalten.

---

## 📬 Kontaktieren Sie uns

Bei Fragen oder Anregungen können Sie uns jederzeit kontaktieren:

- **E-Mail**: service@wanxingai.com  
- **GitHub Issues**：[https://github.com/wanxingai/LightAgent/issues](https://github.com/wanxingai/LightAgent/issues)  

Wir freuen uns auf Ihr Feedback, um LightAgent noch leistungsfähiger zu machen!🚀

- **Weitere Werkzeuge** 🛠️: Kontinuierliche Integration weiterer nützlicher Werkzeuge zur Erfüllung zusätzlicher Anwendungsanforderungen.
- **Weitere Modellunterstützung** 🔄: Kontinuierliche Erweiterung der Unterstützung für weitere große Modelle zur Erfüllung zusätzlicher Anwendungsszenarien.
- **Weitere Funktionen** 🎯: Weitere nützliche Funktionen, kontinuierliche Updates, bleiben Sie dran!
- **Weitere Dokumentation** 📚: Ausführliche Dokumentation, reichhaltige Beispiele, schnelle Einarbeitung, einfache Integration in Ihr Projekt.
- **Weitere Gemeinschaftsunterstützung** 👥: Aktive Entwicklergemeinschaft, die Ihnen jederzeit Hilfe und Antworten bietet.
- **Weitere Leistungsoptimierung** ⚡: Kontinuierliche Optimierung der Leistung zur Erfüllung der Anforderungen an hochgradige Parallelität.
- **Weitere Open-Source-Beiträge** 🌟: Beiträge zum Code sind willkommen, um LightAgent gemeinsam zu verbessern!

---

<p align="center">
  <strong>LightAgent - Machen Sie Intelligenz leichter, machen Sie die Zukunft einfacher.</strong> 🌈
</p>

 
**LightAgent** —— Ein leichtgewichtiges, flexibles und leistungsstarkes aktives Agent-Framework, das Ihnen hilft, intelligente Anwendungen schnell zu erstellen!
