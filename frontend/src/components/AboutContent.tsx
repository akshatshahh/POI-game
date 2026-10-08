export function AboutContent() {
  return (
    <article className="about-content" aria-labelledby="about-heading">
      <header className="about-header">
        <p className="about-eyebrow">USC research project</p>
        <h2 id="about-heading">About POI Game</h2>
        <p className="about-lead">
          The POI Game is a project from the Integrated Media Systems Center in
          the Viterbi School of Engineering at the University of Southern
          California.
        </p>
      </header>

      <section className="about-section" aria-labelledby="about-purpose-heading">
        <h3 id="about-purpose-heading">Understanding visits from GPS data</h3>
        <p>
          The project gathers data about the places people likely visit based on
          locations measured by GPS. Because GPS can be inaccurate, a measured
          location does not necessarily identify which point of interest (POI) a
          person is visiting.
        </p>
        <p>
          The game awards points for indicating where a person most likely
          visited given a GPS location, day of the week, and time of day. We will
          use responses from the game to make better inferences about where
          people visit, even when a measured location is slightly inaccurate.
        </p>
      </section>

      <section className="about-section" aria-labelledby="about-team-heading">
        <h3 id="about-team-heading">Project team</h3>
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

      <section className="about-contact" aria-labelledby="about-contact-heading">
        <div>
          <h3 id="about-contact-heading">Feedback</h3>
          <p>Questions and feedback about the game are welcome.</p>
        </div>
        <a
          className="btn btn-primary"
          href="mailto:akshatdi@usc.edu?cc=hsurani@usc.edu&subject=POI%20Game%20Feedback"
        >
          Contact
        </a>
      </section>
    </article>
  );
}
