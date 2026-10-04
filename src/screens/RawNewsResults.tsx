import type { Article } from '../api/news'

/**
 * Temporary developer view for verifying the real SerpApi retrieval path.
 * Intentionally unstyled/minimal — the polished Brief UI (BriefScreen) still
 * owns the mock-data presentation and will be wired to real summarized
 * stories in a later step.
 */
export function RawNewsResults({ articles }: { articles: Article[] }) {
  return (
    <main className="w-full pt-20 bg-surface min-h-[calc(100vh-140px)]">
      <div className="max-w-3xl mx-auto px-margin-mobile md:px-margin-tablet py-10">
        <div className="mb-6 px-4 py-2 rounded-lg bg-surface-container-low border border-surface-container">
          <p className="font-sans text-label-sm text-on-surface-variant">
            Developer test view — raw SerpApi results, ungrouped and unsummarized.{' '}
            {articles.length} articles retrieved.
          </p>
        </div>

        <div className="space-y-4">
          {articles.map((article) => (
            <article
              key={article.id}
              className="bg-surface-container-lowest rounded-lg p-4 border border-surface-container"
            >
              <span className="font-sans text-label-sm uppercase tracking-widest text-secondary font-semibold">
                {article.topic}
              </span>
              <h2 className="font-serif text-headline-sm text-on-surface mt-1">
                <a
                  href={article.url}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:underline"
                >
                  {article.title}
                </a>
              </h2>
              <div className="font-sans text-label-sm text-on-surface-variant mt-1">
                {article.source}
                {article.published_at && <> &bull; {article.published_at}</>}
              </div>
              {article.snippet && (
                <p className="font-sans text-body-sm text-on-surface mt-2">{article.snippet}</p>
              )}
            </article>
          ))}
        </div>
      </div>
    </main>
  )
}
