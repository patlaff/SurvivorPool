// Buy Me a Coffee account slug — the part after buymeacoffee.com/ in your page URL.
const BUYMEACOFFEE_SLUG = 'patlaff'

export function Footer() {
  return (
    <footer className="border-t border-gray-200 dark:border-gray-700 py-6 px-4">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-center gap-3 text-sm text-gray-500 dark:text-gray-400">
        <span>Enjoying SurvivorPool?</span>
        <a
          href={`https://www.buymeacoffee.com/${BUYMEACOFFEE_SLUG}`}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Buy me a coffee"
          className="inline-flex items-center gap-2 rounded-lg border border-black bg-[#FFDD00] px-4 py-2 font-semibold text-black shadow-sm transition-transform hover:-translate-y-0.5"
        >
          <span aria-hidden="true">☕</span>
          Buy me a coffee
        </a>
      </div>
    </footer>
  )
}
