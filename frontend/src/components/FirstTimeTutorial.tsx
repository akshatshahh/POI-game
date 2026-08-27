import {
  type CSSProperties,
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";

type Placement = "above" | "below" | "left" | "right" | "floating";

interface TutorialStep {
  title: string;
  body: string;
  targetSelectors?: string[];
  preferredPlacement?: Exclude<Placement, "floating">;
}

interface HighlightRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

interface TutorialLayout {
  spotlight: HighlightRect;
  cardTop: number;
  cardLeft: number;
  placement: Placement;
}

interface FirstTimeTutorialProps {
  userId: string;
}

const STORAGE_VERSION = "poi-game:tutorial:v1";
const EDGE_GAP = 16;
const TARGET_GAP = 16;
const SPOTLIGHT_PADDING = 8;

const STEPS: TutorialStep[] = [
  {
    title: "Welcome to POI Game",
    body:
      "Each round shows a recorded GPS visit and nearby places. Your job is to choose the point of interest (POI) the person most likely visited.",
  },
  {
    title: "Use the visit time",
    body:
      "This is when the visit happened. Use the day and time to think about which nearby places were open and likely to be visited then.",
    targetSelectors: ['[data-tutorial="visit-time"]'],
    preferredPlacement: "left",
  },
  {
    title: "Start at the red pin",
    body:
      "The red pin is the recorded GPS location. GPS can be slightly off, so treat it as a clue and compare all of the nearby places.",
    targetSelectors: [".gps-location-marker", ".gps-tooltip"],
    preferredPlacement: "right",
  },
  {
    title: "Choose the most likely place",
    body:
      "Each blue number on the map matches a place in this list. Tap a marker or a list item, then pick the place that best fits both the location and time.",
    targetSelectors: ['[data-tutorial="poi-choices"]'],
    preferredPlacement: "above",
  },
  {
    title: "How the final POI is decided",
    body:
      "After you submit, your answer joins other players' votes. When enough players clearly agree, the leading place becomes the final POI. You earn 5 points for answering and at least 10 more if the final choice matches yours. Split votes may end with no final POI.",
    targetSelectors: ['[data-tutorial="submit-answer"]'],
    preferredPlacement: "above",
  },
];

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), Math.max(min, max));
}

function storageKey(userId: string): string {
  return `${STORAGE_VERSION}:${userId}`;
}

function shouldOpenTutorial(userId: string): boolean {
  try {
    return window.localStorage.getItem(storageKey(userId)) !== "complete";
  } catch {
    return true;
  }
}

export function FirstTimeTutorial({ userId }: FirstTimeTutorialProps) {
  const [isOpen, setIsOpen] = useState(() => shouldOpenTutorial(userId));
  const [stepIndex, setStepIndex] = useState(0);
  const [layout, setLayout] = useState<TutorialLayout | null>(null);
  const cardRef = useRef<HTMLElement>(null);
  const nextButtonRef = useRef<HTMLButtonElement>(null);
  const step = STEPS[stepIndex];

  const finishTutorial = useCallback(() => {
    try {
      window.localStorage.setItem(storageKey(userId), "complete");
    } catch {
      // The tour can still close when browser storage is unavailable.
    }
    setIsOpen(false);
  }, [userId]);

  const goNext = useCallback(() => {
    if (stepIndex === STEPS.length - 1) {
      finishTutorial();
      return;
    }
    setStepIndex((current) => current + 1);
  }, [finishTutorial, stepIndex]);

  const goBack = useCallback(() => {
    setStepIndex((current) => Math.max(0, current - 1));
  }, []);

  const updateLayout = useCallback(() => {
    const card = cardRef.current;
    if (!card || !step.targetSelectors) {
      setLayout(null);
      return;
    }

    const target = step.targetSelectors
      .map((selector) => document.querySelector<HTMLElement>(selector))
      .find((element): element is HTMLElement => element !== null);

    if (!target) {
      setLayout(null);
      return;
    }

    const targetRect = target.getBoundingClientRect();
    const spotlight: HighlightRect = {
      top: Math.max(EDGE_GAP / 2, targetRect.top - SPOTLIGHT_PADDING),
      left: Math.max(EDGE_GAP / 2, targetRect.left - SPOTLIGHT_PADDING),
      width: Math.min(
        window.innerWidth - EDGE_GAP,
        targetRect.width + SPOTLIGHT_PADDING * 2,
      ),
      height: Math.min(
        window.innerHeight - EDGE_GAP,
        targetRect.height + SPOTLIGHT_PADDING * 2,
      ),
    };

    const cardRect = card.getBoundingClientRect();
    const available = {
      above: spotlight.top - EDGE_GAP,
      below: window.innerHeight - (spotlight.top + spotlight.height) - EDGE_GAP,
      left: spotlight.left - EDGE_GAP,
      right: window.innerWidth - (spotlight.left + spotlight.width) - EDGE_GAP,
    };
    const needed = {
      above: cardRect.height + TARGET_GAP,
      below: cardRect.height + TARGET_GAP,
      left: cardRect.width + TARGET_GAP,
      right: cardRect.width + TARGET_GAP,
    };
    const placementCandidates: Array<Exclude<Placement, "floating">> = [
      step.preferredPlacement ?? "below",
      "below",
      "above",
      "right",
      "left",
    ];
    const placements = placementCandidates.filter(
      (value, index, all) => all.indexOf(value) === index,
    );
    const placement =
      placements.find((candidate) => available[candidate] >= needed[candidate]) ??
      "floating";

    let cardTop = clamp(
      spotlight.top + spotlight.height / 2 - cardRect.height / 2,
      EDGE_GAP,
      window.innerHeight - cardRect.height - EDGE_GAP,
    );
    let cardLeft = clamp(
      spotlight.left + spotlight.width / 2 - cardRect.width / 2,
      EDGE_GAP,
      window.innerWidth - cardRect.width - EDGE_GAP,
    );

    if (placement === "above") {
      cardTop = spotlight.top - cardRect.height - TARGET_GAP;
    } else if (placement === "below") {
      cardTop = spotlight.top + spotlight.height + TARGET_GAP;
    } else if (placement === "left") {
      cardLeft = spotlight.left - cardRect.width - TARGET_GAP;
    } else if (placement === "right") {
      cardLeft = spotlight.left + spotlight.width + TARGET_GAP;
    } else {
      cardTop = clamp(
        window.innerHeight - cardRect.height - EDGE_GAP,
        EDGE_GAP,
        window.innerHeight - cardRect.height - EDGE_GAP,
      );
    }

    setLayout({ spotlight, cardTop, cardLeft, placement });
  }, [step]);

  useLayoutEffect(() => {
    if (!isOpen) return;

    const frame = window.requestAnimationFrame(updateLayout);
    const settleTimer = window.setTimeout(updateLayout, 350);
    window.addEventListener("resize", updateLayout);
    window.addEventListener("scroll", updateLayout, true);

    return () => {
      window.cancelAnimationFrame(frame);
      window.clearTimeout(settleTimer);
      window.removeEventListener("resize", updateLayout);
      window.removeEventListener("scroll", updateLayout, true);
    };
  }, [isOpen, updateLayout]);

  useEffect(() => {
    if (!isOpen) return;
    const previouslyFocused =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    return () => previouslyFocused?.focus();
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    nextButtonRef.current?.focus();
  }, [isOpen, stepIndex]);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Tab") {
        const focusable = Array.from(
          cardRef.current?.querySelectorAll<HTMLButtonElement>("button:not(:disabled)") ?? [],
        );
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (!first || !last) return;

        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      } else if (event.key === "Escape") {
        finishTutorial();
      } else if (event.key === "ArrowRight") {
        goNext();
      } else if (event.key === "ArrowLeft" && stepIndex > 0) {
        goBack();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [finishTutorial, goBack, goNext, isOpen, stepIndex]);

  if (!isOpen) return null;

  const cardStyle: CSSProperties | undefined = layout
    ? { top: layout.cardTop, left: layout.cardLeft }
    : undefined;
  const spotlightStyle: CSSProperties | undefined = layout
    ? {
        top: layout.spotlight.top,
        left: layout.spotlight.left,
        width: layout.spotlight.width,
        height: layout.spotlight.height,
      }
    : undefined;

  return (
    <div className={`tutorial-layer${layout ? "" : " tutorial-layer--centered"}`}>
      {layout && <div className="tutorial-spotlight" style={spotlightStyle} aria-hidden="true" />}
      <section
        ref={cardRef}
        className={`tutorial-card${layout ? " tutorial-card--positioned" : " tutorial-card--centered"}`}
        style={cardStyle}
        data-placement={layout?.placement}
        role="dialog"
        aria-modal="true"
        aria-labelledby="tutorial-title"
        aria-describedby="tutorial-description"
      >
        <div className="tutorial-meta">
          <span>Quick tour</span>
          <button type="button" className="tutorial-skip" onClick={finishTutorial}>
            Skip tutorial
          </button>
        </div>

        <div className="tutorial-progress" aria-hidden="true">
          {STEPS.map((tutorialStep, index) => (
            <span
              key={tutorialStep.title}
              className={`tutorial-progress-segment${index <= stepIndex ? " tutorial-progress-segment--active" : ""}`}
            />
          ))}
        </div>

        <p className="tutorial-step-count">
          Step {stepIndex + 1} of {STEPS.length}
        </p>
        <h2 id="tutorial-title">{step.title}</h2>
        <p id="tutorial-description" className="tutorial-description">
          {step.body}
        </p>

        <div className="tutorial-actions">
          <button
            type="button"
            className="tutorial-button tutorial-button--back"
            onClick={goBack}
            disabled={stepIndex === 0}
          >
            Back
          </button>
          <button
            ref={nextButtonRef}
            type="button"
            className="tutorial-button tutorial-button--next"
            onClick={goNext}
          >
            {stepIndex === STEPS.length - 1 ? "Start playing" : "Next"}
          </button>
        </div>
      </section>
    </div>
  );
}
