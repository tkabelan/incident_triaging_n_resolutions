import { FormEvent, useEffect, useRef, useState } from "react";

import { processErrorStream, ProcessErrorApiError } from "./api/processError";
import type {
  ProcessProgressEvent,
  ProcessErrorResponse,
  ProcessStreamEvent,
  StageData,
  WebSearchItem,
} from "./types/agent";

const DEFAULT_ERROR =
  "[CANNOT_OPEN_SOCKET] Can not open socket: [\"tried to connect to ('127.0.0.1', 37311), but an error occurred: [Errno 111] Connection refused\"]";

const STAGE_ORDER = [
  "chroma_db",
  "planner",
  "primary_llm",
  "verification_llm",
  "web_search",
  "refinement_llm",
  "reflection",
  "human_review",
] as const;

const STAGE_LABELS: Record<(typeof STAGE_ORDER)[number], string> = {
  chroma_db: "Chroma DB lookup",
  planner: "Planner decision",
  primary_llm: "Primary LLM",
  verification_llm: "Verification LLM",
  web_search: "Web search",
  refinement_llm: "Refinement LLM",
  reflection: "Reflection",
  human_review: "Human review",
};

type FriendlyStep = {
  icon: string;
  title: string;
  description: string;
};

type LiveStep = {
  stage: string;
  title: string;
  description: string;
  status: "running" | "complete" | "failed";
};

function toTitleCase(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatStatus(value: string) {
  return value.replace(/_/g, " ");
}

function formatRowId(value: string) {
  return value === "manual-1" ? "Manual entry" : value;
}

function formatConfidence(value?: number | null) {
  if (value === null || value === undefined) {
    return "Not available";
  }
  return `${Math.round(value * 100)}%`;
}

function formatScore(value?: number) {
  if (value === undefined || value === null) {
    return "Not available";
  }
  return value.toFixed(2);
}

function getStageReason(stage: StageData): string {
  return (
    stage.reasoning ??
    stage.decision_reason ??
    stage.reason ??
    stage.error?.message ??
    "No additional detail returned."
  );
}

function renderStageMeta(stage: StageData, stageKey: string) {
  if (stageKey !== "chroma_db") {
    return null;
  }

  return (
    <>
      <div>
        <dt>Evidence count</dt>
        <dd>{stage.evidence_count ?? 0}</dd>
      </div>
      <div>
        <dt>Top match score</dt>
        <dd>{stage.top_match_score !== undefined && stage.top_match_score !== null ? formatScore(stage.top_match_score) : "Not available"}</dd>
      </div>
      <div>
        <dt>Direct match threshold</dt>
        <dd>
          {stage.direct_match_threshold !== undefined && stage.direct_match_threshold !== null
            ? formatScore(stage.direct_match_threshold)
            : "Not available"}
        </dd>
      </div>
      <div>
        <dt>Direct match</dt>
        <dd>{stage.direct_match ? "Yes" : "No"}</dd>
      </div>
    </>
  );
}

function renderStageItems(stage: StageData, stageKey: string) {
  if (stageKey !== "chroma_db" || !stage.items || stage.items.length === 0) {
    return null;
  }

  return (
    <div className="stage-items">
      <p className="stage-items-label">ChromaDB results</p>
      <div className="stage-item-list">
        {stage.items.map((item, index) => {
          const kbId = typeof item.kb_id === "string" ? item.kb_id : "unknown";
          const title = typeof item.title === "string" ? item.title : "Untitled match";
          const category = typeof item.category === "string" ? item.category : "Not available";
          const resolution =
            typeof item.resolution === "string" ? item.resolution : "No resolution returned.";
          const score =
            typeof item.score === "number" ? formatScore(item.score) : "Not available";

          return (
            <article key={`${kbId}-${index}`} className="stage-item-card">
              <div className="stage-item-header">
                <h4>{title}</h4>
                <span>Score {score}</span>
              </div>
              <p className="stage-item-meta">
                <strong>KB ID:</strong> {kbId}
              </p>
              <p className="stage-item-meta">
                <strong>Category:</strong> {category}
              </p>
              <p className="stage-item-meta">
                <strong>Resolution:</strong> {resolution}
              </p>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function getWebSearchItems(result: ProcessErrorResponse): WebSearchItem[] {
  const webStage = result.agent_trace.stages.web_search;
  const items = webStage?.items ?? [];
  return items as WebSearchItem[];
}

function buildFriendlySteps(result: ProcessErrorResponse): FriendlyStep[] {
  const stages = result.agent_trace.stages;
  const steps: FriendlyStep[] = [
    {
      icon: "📂",
      title: "Parsing the error",
      description: "The app cleaned the input and prepared it for retrieval and reasoning.",
    },
    {
      icon: "🗂️",
      title: stages.chroma_db?.direct_match ? "Found in the knowledge base" : "Checking the knowledge base",
      description: stages.chroma_db?.direct_match
        ? "A strong KB match was found, so the agent could reuse prior knowledge."
        : "The agent looked for similar issues and grounded evidence in ChromaDB.",
    },
  ];

  if (stages.primary_llm?.status === "pass") {
    steps.push({
      icon: "🧠",
      title: "Calling the classifier",
      description: "The primary model classified the error and proposed a resolution.",
    });
  } else if (stages.primary_llm?.status === "fail") {
    steps.push({
      icon: "🧠",
      title: "Classifier could not complete",
      description: "The primary model attempted classification but did not finish successfully.",
    });
  }

  if (stages.verification_llm?.status === "pass") {
    steps.push({
      icon: "✅",
      title: stages.verification_llm.passed ? "Verification passed" : "Verification raised doubt",
      description: stages.verification_llm.passed
        ? "A second model checked the answer and considered it reliable."
        : "A second model reviewed the answer and requested more evidence.",
    });
  }

  if (stages.web_search?.status === "pass") {
    steps.push({
      icon: "🔎",
      title: "Searching the web",
      description: "The agent pulled external evidence because the internal answer was not enough.",
    });
  }

  if (stages.refinement_llm?.status === "pass") {
    steps.push({
      icon: "🛠️",
      title: "Refining the answer",
      description: "The model combined the new evidence with the earlier context to improve the result.",
    });
  }

  if (result.agent_trace.kb_update_triggered) {
    steps.push({
      icon: "📚",
      title: "Updating the knowledge base",
      description: "The verified result was saved so similar errors can be answered faster next time.",
    });
  }

  if (stages.human_review?.status === "pass") {
    steps.push({
      icon: "🧑‍💻",
      title: "Routing to human review",
      description: "The agent stopped safely because it could not reach a reliable autonomous answer.",
    });
  }

  return steps;
}

function App() {
  const [errorText, setErrorText] = useState(DEFAULT_ERROR);
  const [forceWebSearch, setForceWebSearch] = useState(false);
  const [result, setResult] = useState<ProcessErrorResponse | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [liveSteps, setLiveSteps] = useState<LiveStep[]>([]);
  const liveStepsContainerRef = useRef<HTMLDivElement | null>(null);
  const activeStepRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isSubmitting || !liveStepsContainerRef.current || !activeStepRef.current) {
      return;
    }

    const container = liveStepsContainerRef.current;
    const activeStep = activeStepRef.current;
    const targetTop =
      activeStep.offsetTop - container.clientHeight / 2 + activeStep.clientHeight / 2;

    container.scrollTo({
      top: Math.max(0, targetTop),
      behavior: "smooth",
    });
  }, [isSubmitting, liveSteps]);

  async function startAnalysis(forceSearchOverride?: boolean) {
    const trimmed = errorText.trim();
    if (!trimmed || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setRequestError(null);
    setResult(null);
    setLiveSteps([]);

    try {
      await processErrorStream(
        {
          error_text: trimmed,
          force_web_search: forceSearchOverride ?? forceWebSearch,
        },
        (event: ProcessStreamEvent) => {
          if (event.type === "progress") {
            setLiveSteps((current) => {
              const completed = current.map((step) =>
                step.status === "running" ? { ...step, status: "complete" as const } : step,
              );
              return [
                ...completed,
                {
                  stage: event.stage,
                  title: event.title,
                  description: event.description,
                  status: event.status === "failed" ? "failed" : "running",
                },
              ];
            });
            return;
          }
          if (event.type === "result") {
            setLiveSteps((current) =>
              current.map((step) =>
                step.status === "running" ? { ...step, status: "complete" as const } : step,
              ),
            );
            setResult(event.payload);
            return;
          }
          if (event.type === "error") {
            setLiveSteps((current) =>
              current.map((step) =>
                step.status === "running" ? { ...step, status: "failed" as const } : step,
              ),
            );
            setRequestError(event.payload.message);
          }
        },
      );
    } catch (error) {
      if (error instanceof ProcessErrorApiError) {
        setRequestError(`${error.message} (HTTP ${error.status})`);
      } else if (error instanceof Error) {
        setRequestError(error.message);
      } else {
        setRequestError("The request failed.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await startAnalysis();
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">Incident Agent</p>
        <h1>Enter error details</h1>
        <p className="hero-copy">
          This first frontend slice is focused on submission flow only. It sends one error to the
          FastAPI backend and returns the backend response for the next UI steps.
        </p>
      </section>

      <section className="panel">
        <form className="error-form" onSubmit={handleSubmit}>
          <label className="field-label" htmlFor="errorText">
            Error text
          </label>
          <textarea
            id="errorText"
            className="error-textarea"
            value={errorText}
            onChange={(event) => setErrorText(event.target.value)}
            rows={8}
            placeholder="Paste one error message here"
          />

          <div className="preference-card">
            <div className="preference-copy">
              <p className="section-label">Optional evidence mode</p>
              <h3>Always run web search</h3>
              <p>
                Use this when non-experts want plain external references even if the model already
                verified the answer.
              </p>
            </div>
            <label className="checkbox-row" htmlFor="forceWebSearch">
              <input
                id="forceWebSearch"
                type="checkbox"
                checked={forceWebSearch}
                onChange={(event) => setForceWebSearch(event.target.checked)}
              />
              <span>Enable forced web search</span>
            </label>
          </div>

          <div className="actions">
            <button className="submit-button" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Analyzing..." : "Analyze Error"}
            </button>
            <p className="helper-text">
              Backend endpoint: <code>POST /api/v1/errors/process</code>
            </p>
          </div>
        </form>
      </section>

      {isSubmitting ? (
        <section className="panel">
          <div className="timeline-header">
            <div>
              <p className="section-label">Live progress</p>
              <h2>Processing right now</h2>
            </div>
            <p className="timeline-helper">
              The backend is streaming these steps as the workflow runs.
            </p>
          </div>

          <div className="friendly-steps" ref={liveStepsContainerRef}>
            {liveSteps.length > 0 ? (
              liveSteps.map((step, index) => (
                <div
                  key={`${step.stage}-${index}`}
                  ref={step.status === "running" ? activeStepRef : null}
                  className="progress-row"
                >
                  <div className="progress-copy">
                    <span>
                      <strong>{step.title}</strong>
                      {" - "}
                      {step.description}
                    </span>
                  </div>
                  <span className={`progress-state progress-${step.status}`}>
                    {step.status === "running"
                      ? "In progress"
                      : step.status === "failed"
                        ? "fail"
                        : "✅"}
                  </span>
                </div>
              ))
            ) : (
              <div className="progress-row">
                <div className="progress-copy">
                  <span>
                    <strong>Starting the workflow</strong>
                    {" - "}The backend has accepted the request and is beginning the agent run.
                  </span>
                </div>
                <span className="progress-state progress-running">In progress</span>
              </div>
            )}
          </div>
        </section>
      ) : null}

      {requestError ? (
        <section className="panel status-panel error-panel">
          <h2>Request Failed</h2>
          <p>{requestError}</p>
        </section>
      ) : null}

      {result ? (
        <>
          <section className="panel result-panel">
            <div className="result-header">
              <div>
                <p className="section-label">Outcome summary</p>
                <h2>{toTitleCase(result.agent_trace.final_status)}</h2>
              </div>
              <span className={`status-pill status-${result.status}`}>{formatStatus(result.status)}</span>
            </div>

            <dl className="result-grid">
              <div>
                <dt>Classification</dt>
                <dd className="classification-primary">
                  {result.classification?.main_category ?? result.agent_trace.main_category ?? "Not available"}
                </dd>
              </div>
              <div>
                <dt>Subcategory</dt>
                <dd className="classification-secondary">
                  {result.classification?.subcategory ?? result.agent_trace.subcategory ?? "Not available"}
                </dd>
              </div>
              <div>
                <dt>Row ID</dt>
                <dd>{formatRowId(result.row_id)}</dd>
              </div>
              <div>
                <dt>Outcome source</dt>
                <dd>{result.agent_trace.outcome_source ? toTitleCase(result.agent_trace.outcome_source) : "Not available"}</dd>
              </div>
              <div>
                <dt>Resolution</dt>
                <dd>{result.agent_trace.resolution ?? "Not available"}</dd>
              </div>
            </dl>

            {result.models ? (
              <div className="model-block">
                <p className="section-label">Models used</p>
                <dl className="model-grid">
                  <div>
                    <dt>Primary classification</dt>
                    <dd>{result.models.primary_classification}</dd>
                  </div>
                  <div>
                    <dt>Verification</dt>
                    <dd>{result.models.verification}</dd>
                  </div>
                </dl>
              </div>
            ) : null}

            <div className="explanation-block">
              <p className="section-label">What happened</p>
              <p>{result.agent_trace.branch_explanation ?? "No explanation returned."}</p>
            </div>
          </section>

          <section className="panel">
            <div className="timeline-header">
              <div>
                <p className="section-label">Agent walkthrough</p>
                <h2>Short reasoning steps</h2>
              </div>
              <p className="timeline-helper">
                This is a simple explanation of what the agent did, without raw internal reasoning.
              </p>
            </div>

            <div className="friendly-steps">
              {buildFriendlySteps(result).map((step, index) => (
                <div key={`${step.title}-${index}`} className="progress-row final-progress-row">
                  <div className="progress-copy">
                    <span>
                      <strong>
                        {step.icon} {step.title}
                      </strong>
                      {" - "}
                      {step.description}
                    </span>
                  </div>
                  <span className="progress-state progress-complete">✅</span>
                </div>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="timeline-header">
              <div>
                <p className="section-label">Key scores</p>
                <h2>Confidence and decision signals</h2>
              </div>
              <p className="timeline-helper">These are the main scores and final KB outcome indicators.</p>
            </div>

            <div className="score-grid">
              <article className="score-card">
                <p className="score-label">Primary classification</p>
                <p className="score-value">
                  {formatConfidence(result.agent_trace.stages.primary_llm?.confidence)}
                </p>
              </article>
              <article className="score-card">
                <p className="score-label">Verification</p>
                <p className="score-value">
                  {formatConfidence(result.agent_trace.stages.verification_llm?.confidence)}
                </p>
              </article>
              <article className="score-card">
                <p className="score-label">Refinement</p>
                <p className="score-value">
                  {formatConfidence(result.agent_trace.stages.refinement_llm?.confidence)}
                </p>
              </article>
              <article className="score-card">
                <p className="score-label">Web results</p>
                <p className="score-value">{result.agent_trace.stages.web_search?.results ?? 0}</p>
              </article>
            </div>

            <div className="kb-panel">
              <div>
                <p className="section-label">KB update</p>
                <h3>{result.agent_trace.kb_update_triggered ? "Knowledge base updated" : "No KB update recorded"}</h3>
              </div>
              <dl className="kb-grid">
                <div>
                  <dt>Triggered</dt>
                  <dd>{result.agent_trace.kb_update_triggered ? "Yes" : "No"}</dd>
                </div>
                <div>
                  <dt>Reference</dt>
                  <dd>{result.agent_trace.kb_update_reference ?? "Not available"}</dd>
                </div>
                <div className="kb-grid-wide">
                  <dt>Reason</dt>
                  <dd>{result.agent_trace.kb_update_reason ?? "No KB update reason returned."}</dd>
                </div>
              </dl>
            </div>
          </section>

          <section className="panel">
            <div className="timeline-header">
              <div>
                <p className="section-label">Agent steps</p>
                <h2>Stage timeline (WIP)</h2>
              </div>
              <p className="timeline-helper">Each card shows whether a stage ran, skipped, or failed.</p>
            </div>

            <div className="timeline-grid">
              {STAGE_ORDER.map((stageKey) => {
                const stage = result.agent_trace.stages[stageKey];
                if (!stage) {
                  return null;
                }

                return (
                  <article key={stageKey} className={`timeline-card timeline-${stage.status}`}>
                    <div className="timeline-card-header">
                      <h3>{STAGE_LABELS[stageKey]}</h3>
                      <span className={`stage-badge stage-${stage.status}`}>{formatStatus(stage.status)}</span>
                    </div>

                    <dl className="timeline-meta">
                      <div>
                        <dt>Confidence</dt>
                        <dd>{formatConfidence(stage.confidence)}</dd>
                      </div>
                      {renderStageMeta(stage, stageKey)}
                      {"attempts" in stage ? (
                        <div>
                          <dt>Attempts</dt>
                          <dd>{stage.attempts ?? 0}</dd>
                        </div>
                      ) : null}
                      {"passed" in stage ? (
                        <div>
                          <dt>Passed</dt>
                          <dd>{stage.passed === null || stage.passed === undefined ? "Not available" : stage.passed ? "Yes" : "No"}</dd>
                        </div>
                      ) : null}
                      {"needs_web_search" in stage ? (
                        <div>
                          <dt>Needs web search</dt>
                          <dd>
                            {stage.needs_web_search === null || stage.needs_web_search === undefined
                              ? "Not available"
                              : stage.needs_web_search
                                ? "Yes"
                                : "No"}
                          </dd>
                        </div>
                      ) : null}
                    </dl>

                    <p className="timeline-reason">{getStageReason(stage)}</p>
                    {renderStageItems(stage, stageKey)}
                  </article>
                );
              })}
            </div>
          </section>

          <section className="panel">
            <div className="timeline-header">
              <div>
                <p className="section-label">External evidence</p>
                <h2>Web search results</h2>
              </div>
              <p className="timeline-helper">
                These links only appear if the agent used Tavily during the run.
              </p>
            </div>

            {getWebSearchItems(result).length > 0 ? (
              <div className="evidence-list">
                {getWebSearchItems(result).map((item, index) => (
                  <article key={`${item.url ?? "result"}-${index}`} className="evidence-card">
                    <div className="evidence-header">
                      <h3>{item.title ?? "Untitled result"}</h3>
                      <span className="evidence-score">Score {formatScore(item.score)}</span>
                    </div>
                    <p className="evidence-content">{item.content ?? "No excerpt returned."}</p>
                    {item.url ? (
                      <a className="evidence-link" href={item.url} target="_blank" rel="noreferrer">
                        Open source
                      </a>
                    ) : null}
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-evidence">
                <p>No web evidence was returned for this run.</p>
              </div>
            )}
          </section>
        </>
      ) : (
        <section className="panel empty-panel">
          <p className="section-label">Waiting for submission</p>
          <p>Submit one error to see the backend summary, timeline, scores, evidence, and KB status.</p>
        </section>
      )}
    </main>
  );
}

export default App;
