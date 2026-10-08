export function AboutContent() {
  return (
    <article
      className="about-content about-content--page"
      aria-labelledby="about-heading"
    >
      <header className="about-header">
        <p className="about-eyebrow">Point of Interest (POI)</p>
        <h1 id="about-heading">What is the POI Game?</h1>
        <p className="about-lead">
          POI stands for <strong>Point of Interest</strong>: a real-world place
          someone may visit, such as a cafe, store, park, school, or office. The
          game asks you to decide which nearby place a person most likely visited.
        </p>
        <div className="about-definition" aria-label="POI definition">
          <span aria-hidden="true">POI</span>
          <div>
            <strong>Point of Interest</strong>
            <p>A useful or meaningful place shown near a measured GPS location.</p>
          </div>
        </div>
      </header>

      <section className="about-section" aria-labelledby="about-play-heading">
        <h3 id="about-play-heading">How the game works</h3>
        <ol className="about-steps">
          <li>
            <span className="about-step-number">1</span>
            <div>
              <h4>Read the clues</h4>
              <p>Look at the GPS marker, nearby places, day, and time.</p>
            </div>
          </li>
          <li>
            <span className="about-step-number">2</span>
            <div>
              <h4>Choose likely places</h4>
              <p>Select one or more POIs that the person may have visited.</p>
            </div>
          </li>
          <li>
            <span className="about-step-number">3</span>
            <div>
              <h4>Submit and score</h4>
              <p>Earn points while adding a useful human judgment to the project.</p>
            </div>
          </li>
        </ol>
      </section>

      <section className="about-section" aria-labelledby="about-purpose-heading">
        <h3 id="about-purpose-heading">Why the project matters</h3>
        <p>
          GPS is not perfectly accurate. In a busy area, one measured location
          can sit between several nearby businesses or buildings, so the nearest
          place is not always the place someone actually visited.
        </p>
        <p>
          Players add context that a coordinate alone cannot provide. Combined
          responses help the research team make better inferences about visits
          from imperfect GPS locations, days of the week, and times of day.
        </p>
        <div className="about-questions">
          <details>
            <summary>Why isn't the nearest place always correct?</summary>
            <p>
              GPS readings can drift, especially around tall buildings or places
              that are close together. A marker may appear beside the actual visit.
            </p>
          </details>
          <details>
            <summary>What does my answer contribute?</summary>
            <p>
              Your choice becomes one human judgment that researchers can compare
              with the measured location and visit time. Many judgments make the
              overall signal more useful.
            </p>
          </details>
        </div>
      </section>

      <section className="about-section" aria-labelledby="about-team-heading">
        <h3 id="about-team-heading">The project and team</h3>
        <p>
          The POI Game is a project from the Integrated Media Systems Center in
          the Viterbi School of Engineering at the University of Southern
          California.
        </p>
        <dl className="about-credits">
          <div>
            <dt>Conceived by</dt>
            <dd>John Krumm</dd>
          </div>
          <div>
            <dt>Software design and development</dt>
            <dd>
              Akshat Divyang Shah (
              <a href="mailto:akshatdi@usc.edu">akshatdi@usc.edu</a>) and Hitansh
              Surani (<a href="mailto:hsurani@usc.edu">hsurani@usc.edu</a>)
            </dd>
          </div>
        </dl>
      </section>

    </article>
  );
}
