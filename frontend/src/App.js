import React, { useState, useRef, useEffect } from "react";
import "./App.css";

const SUGGESTIONS = [
  "What's the difference between HMO and PPO plans?",
  "Explain deductible vs out-of-pocket maximum",
  "What does a Silver plan cover?",
  "How do tax credits work for ACA plans?",
];

function renderMarkdown(text) {
  if (!text) return "";
  return text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/^###\s+(.+)$/gm, "<h4>$1</h4>")
    .replace(/^[-•]\s+(.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`)
    .replace(/\n\n/g, "</p><p>")
    .replace(/\n/g, "<br/>")
    .replace(/^(.+)$/, "<p>$1</p>");
}

function MD({ text }) {
  return (
    <div
      className="md"
      dangerouslySetInnerHTML={{ __html: renderMarkdown(text) }}
    />
  );
}

function PlanCard({ plan, onSelect, selectedPlan }) {
  const isSelected = selectedPlan?.id === plan.id;

  return (
    <div className={`plan-card ${isSelected ? "selected-plan-card" : ""}`}>
      <div className="plan-card-top">
        <div>
          <h3>{plan.name}</h3>
          <p>{plan.issuer}</p>
        </div>

        <span className="metal-pill">{plan.metal_level || "Plan"}</span>
      </div>

      <div className="plan-grid">
        <div>
          <span>Monthly Premium</span>
          <strong>${plan.premium_w_credit ?? plan.premium ?? "N/A"}</strong>
        </div>

        <div>
          <span>Deductible</span>
          <strong>${plan.deductible ?? "N/A"}</strong>
        </div>

        <div>
          <span>Out-of-pocket Max</span>
          <strong>${plan.out_of_pocket_max ?? "N/A"}</strong>
        </div>

        <div>
          <span>Type</span>
          <strong>{plan.type || "N/A"}</strong>
        </div>
      </div>

      <div className="plan-extra">
        <span>Quality: {plan.quality_rating || "Not rated"}</span>
        <span>HSA: {plan.hsa_eligible ? "Yes" : "No"}</span>
      </div>

      <button className="select-plan-btn" onClick={() => onSelect(plan)}>
        {isSelected ? "Selected" : "Select for drug check"}
      </button>

      <div className="plan-links">
        {plan.benefits_url && (
          <a href={plan.benefits_url} target="_blank" rel="noopener noreferrer">
            Benefits
          </a>
        )}

        {plan.network_url && (
          <a href={plan.network_url} target="_blank" rel="noopener noreferrer">
            Network
          </a>
        )}

        {plan.formulary_url && (
          <a href={plan.formulary_url} target="_blank" rel="noopener noreferrer">
            Formulary
          </a>
        )}
      </div>
    </div>
  );
}
function Message({ msg }) {
  const isUser = msg.role === "user";

  return (
    <div className={`msg ${isUser ? "msg-user" : "msg-bot"}`}>
      {!isUser && <div className="avatar bot-avatar">C</div>}

      <div className={`bubble ${isUser ? "user-bubble" : "bot-bubble"}`}>
        {isUser ? (
          <span>{msg.content}</span>
        ) : (
          <>
            <MD text={msg.answer} />

            {msg.sources?.length > 0 && (
              <div className="source-tags">
                {msg.sources.map((source) => (
                  <span key={source} className="source-tag">
                    {source}
                  </span>
                ))}
              </div>
            )}

            {msg.steps?.length > 0 && (
              <details className="trace">
                <summary className="trace-toggle">
                  {msg.steps.length} data source
                  {msg.steps.length !== 1 ? "s" : ""} used
                </summary>

                <div className="trace-list">
                  {msg.steps.map((step, index) => (
                    <div key={index} className="trace-item">
                      {step}
                    </div>
                  ))}
                </div>
              </details>
            )}
          </>
        )}
      </div>

      {isUser && <div className="avatar user-avatar">U</div>}
    </div>
  );
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  const [loading, setLoading] = useState(false);
  const [plansLoading, setPlansLoading] = useState(false);
  const [drugLoading, setDrugLoading] = useState(false);
  const [error, setError] = useState(null);

  const [plans, setPlans] = useState([]);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [drugResult, setDrugResult] = useState(null);

  const [intake, setIntake] = useState({
    zip_code: "",
    state: "",
    age: "",
    income: "",
    gender: "Female",
    uses_tobacco: false,
    utilization_level: "Medium",
    year: 2024,
  });

  const [drugName, setDrugName] = useState("");

  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, plans, selectedPlan, drugResult]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 120) + "px";
    }
  }, [input]);

  function buildContext(question) {
    return `
User question: ${question}

Current user profile:
ZIP code: ${intake.zip_code || "not provided"}
State: ${intake.state || "not provided"}
Age: ${intake.age || "not provided"}
Income: ${intake.income || "not provided"}
Gender: ${intake.gender || "not provided"}
Tobacco use: ${intake.uses_tobacco ? "Yes" : "No"}
Usage level: ${intake.utilization_level || "not provided"}
Year: ${intake.year || "not provided"}

Plans currently shown in UI:
${
  plans.length > 0
    ? plans
        .map(
          (p, i) => `
${i + 1}. ${p.name}
Plan ID: ${p.id}
Issuer: ${p.issuer}
Metal level: ${p.metal_level}
Type: ${p.type}
Premium: ${p.premium_w_credit ?? p.premium ?? "N/A"}
Deductible: ${p.deductible ?? "N/A"}
Out-of-pocket max: ${p.out_of_pocket_max ?? "N/A"}
Quality rating: ${p.quality_rating ?? "Not rated"}
HSA eligible: ${p.hsa_eligible ? "Yes" : "No"}
Formulary URL: ${p.formulary_url || "not available"}`
        )
        .join("\n")
    : "No plans searched yet."
}

Selected plan:
${
  selectedPlan
    ? `
Plan name: ${selectedPlan.name}
Plan ID: ${selectedPlan.id}
Issuer: ${selectedPlan.issuer}
Metal level: ${selectedPlan.metal_level}
Type: ${selectedPlan.type}
Premium: ${selectedPlan.premium_w_credit ?? selectedPlan.premium ?? "N/A"}
Deductible: ${selectedPlan.deductible ?? "N/A"}
Out-of-pocket max: ${selectedPlan.out_of_pocket_max ?? "N/A"}
Quality rating: ${selectedPlan.quality_rating ?? "Not rated"}
HSA eligible: ${selectedPlan.hsa_eligible ? "Yes" : "No"}
Formulary URL: ${selectedPlan.formulary_url || "not available"}`
    : "No plan selected yet."
}

Latest drug coverage check:
${
  drugResult
    ? `
Drug: ${drugResult.drug}
Coverage status: ${drugResult.coverage_status}
Covered: ${drugResult.covered ? "Yes" : "No"}
Important note: If coverage_status is DataNotProvided, do not say the drug is not covered. Say CMS does not provide data for this exact drug-plan combination.`
    : "No drug checked yet."
}
`;
  }

  async function ask(q) {
    const question = q || input;

    if (!question.trim() || loading) return;

    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setLoading(true);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    try {
      const res = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          question: buildContext(question),
          history: messages.map((m) => ({
            role: m.role === "user" ? "user" : "assistant",
            content: m.role === "user" ? m.content : m.answer,
          })),
        }),
      });

      clearTimeout(timeoutId);

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Server error");
      }

      setMessages((prev) => [...prev, { role: "assistant", ...data }]);
    } catch (e) {
      if (e.name === "AbortError") {
        setError("The AI response took too long. Please try again.");
      } else {
        setError(e.message);
      }
    } finally {
      setLoading(false);
    }
  }

  async function searchPlans(e) {
    e.preventDefault();

    setError(null);
    setPlans([]);
    setSelectedPlan(null);
    setDrugResult(null);
    setPlansLoading(true);

    if (!intake.zip_code || !intake.state || !intake.age || !intake.income) {
      setError("Please enter ZIP code, state, age, and income.");
      setPlansLoading(false);
      return;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 25000);

    try {
      const res = await fetch("/plans/search-ui", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          ...intake,
          state: intake.state.toUpperCase(),
          age: Number(intake.age),
          income: Number(intake.income),
          year: Number(intake.year),
        }),
      });

      clearTimeout(timeoutId);

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Plan search failed");
      }

      setPlans(data.plans || []);

      if (!data.plans || data.plans.length === 0) {
        setError("No plans found for this ZIP/state/year.");
      }
    } catch (e) {
      if (e.name === "AbortError") {
        setError(
          "CMS API is taking too long. Please try again later or use your private CMS API key."
        );
      } else {
        setError(e.message);
      }
    } finally {
      setPlansLoading(false);
    }
  }

  async function checkDrug(e) {
    e.preventDefault();

    if (!selectedPlan) {
      setError("Please select a plan first.");
      return;
    }

    if (!drugName.trim()) {
      setError("Please enter a drug name.");
      return;
    }

    setError(null);
    setDrugResult(null);
    setDrugLoading(true);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 25000);

    try {
      const res = await fetch("/drugs/check-ui", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          drug_name: drugName,
          plan_id: selectedPlan.id,
          year: Number(intake.year),
        }),
      });

      clearTimeout(timeoutId);

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Drug coverage check failed");
      }

      setDrugResult(data);
    } catch (e) {
      if (e.name === "AbortError") {
        setError("Drug coverage check took too long. Please try again.");
      } else {
        setError(e.message);
      }
    } finally {
      setDrugLoading(false);
    }
  }

  function onKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      ask();
    }
  }

  function handleSelectPlan(plan) {
    setSelectedPlan(plan);
    setDrugResult(null);
    setError(null);
  }

  function renderDrugMessage() {
    if (!drugResult) return null;

    if (drugResult.coverage_status === "DataNotProvided") {
      return (
        <>
          <p>
            CMS does not provide formulary data for this exact drug-plan
            combination.
          </p>
          <p>
            This does <strong>not</strong> mean the drug is not covered. Please
            check the plan’s official formulary link or insurer website.
          </p>

          {selectedPlan?.formulary_url && (
            <a
              href={selectedPlan.formulary_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Open official formulary
            </a>
          )}
        </>
      );
    }

    if (drugResult.covered) {
      return <p>This medication appears to be covered under the selected plan.</p>;
    }

    return <p>This medication appears not covered under the selected plan.</p>;
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-brand">
          <div className="brand-icon">+</div>
          <span className="brand-name">CoverBot</span>
        </div>

        <div className="header-meta">
          AI Health Insurance Guide · CMS Marketplace API
        </div>

        <div className="header-dot">
          <span className="online-dot" />
          Online
        </div>
      </header>

      <div className="body">
        <div className="welcome compact-welcome">
          <h1 className="welcome-title">Find and compare plans</h1>

          <p className="welcome-sub">
            Enter basic details, compare ACA plans, then check whether a
            medication is covered.
          </p>

          <form className="intake-form" onSubmit={searchPlans}>
            <input
              placeholder="ZIP code"
              value={intake.zip_code}
              onChange={(e) =>
                setIntake({ ...intake, zip_code: e.target.value })
              }
            />

            <input
              placeholder="State, ex: IL"
              value={intake.state}
              onChange={(e) =>
                setIntake({
                  ...intake,
                  state: e.target.value.toUpperCase(),
                })
              }
            />

            <input
              placeholder="Age"
              type="number"
              value={intake.age}
              onChange={(e) => setIntake({ ...intake, age: e.target.value })}
            />

            <input
              placeholder="Income"
              type="number"
              value={intake.income}
              onChange={(e) =>
                setIntake({ ...intake, income: e.target.value })
              }
            />

            <select
              value={intake.gender}
              onChange={(e) =>
                setIntake({ ...intake, gender: e.target.value })
              }
            >
              <option>Female</option>
              <option>Male</option>
            </select>

            <select
              value={intake.utilization_level}
              onChange={(e) =>
                setIntake({
                  ...intake,
                  utilization_level: e.target.value,
                })
              }
            >
              <option>Low</option>
              <option>Medium</option>
              <option>High</option>
            </select>

            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={intake.uses_tobacco}
                onChange={(e) =>
                  setIntake({
                    ...intake,
                    uses_tobacco: e.target.checked,
                  })
                }
              />
              Tobacco use
            </label>

            <button
              className="primary-wide"
              type="submit"
              disabled={plansLoading}
            >
              {plansLoading ? "Searching plans..." : "Search Plans"}
            </button>
          </form>
        </div>

        {plans.length > 0 && (
          <section className="plans-section">
            <h2>Compare Plans</h2>

            <div className="plans-grid">
              {plans.map((plan) => (
                <PlanCard
                  key={plan.id}
                  plan={plan}
                  selectedPlan={selectedPlan}
                  onSelect={handleSelectPlan}
                />
              ))}
            </div>
          </section>
        )}

        {selectedPlan && (
          <section className="drug-section">
            <h2>Drug Coverage Checker</h2>

            <p>
              Selected plan: <strong>{selectedPlan.name}</strong>
            </p>

            <form className="drug-form" onSubmit={checkDrug}>
              <input
                placeholder="Enter medication, ex: metformin"
                value={drugName}
                onChange={(e) => setDrugName(e.target.value)}
              />

              <button type="submit" disabled={drugLoading}>
                {drugLoading ? "Checking..." : "Check Coverage"}
              </button>
            </form>

            {drugResult && (
              <div
                className={`drug-result ${
                  drugResult.coverage_status === "DataNotProvided"
                    ? "unknown"
                    : drugResult.covered
                    ? "covered"
                    : "not-covered"
                }`}
              >
                <strong>{drugResult.drug}</strong>

                <p>
                  Coverage status:{" "}
                  <strong>{drugResult.coverage_status}</strong>
                </p>

                {renderDrugMessage()}
              </div>
            )}
          </section>
        )}

        <div className="messages">
          {messages.length === 0 && (
            <div className="suggestions">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  className="suggestion-btn"
                  onClick={() => ask(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}

          {messages.map((message, index) => (
            <Message key={index} msg={message} />
          ))}

          {loading && (
            <div className="msg msg-bot">
              <div className="avatar bot-avatar">C</div>
              <div className="bubble bot-bubble typing-bubble">
                <span />
                <span />
                <span />
              </div>
            </div>
          )}

          {error && <div className="error-msg">⚠ {error}</div>}

          <div ref={bottomRef} />
        </div>
      </div>

      <div className="input-area">
        <div className="input-container">
          <textarea
            ref={textareaRef}
            className="input-field"
            placeholder="Ask about plans, coverage, costs..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKey}
            rows={1}
            disabled={loading}
          />

          <button
            className="send-button"
            onClick={() => ask()}
            disabled={loading || !input.trim()}
          >
            {loading ? <span className="loader" /> : "➤"}
          </button>
        </div>

        <p className="input-hint">
          Press Enter to send · Shift+Enter for new line · Data from CMS
          Marketplace API
        </p>
      </div>
    </div>
  );
}