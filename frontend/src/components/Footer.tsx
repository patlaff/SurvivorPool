// Your Buy Me a Coffee username — the part after buymeacoffee.com/ in your page URL.
// e.g. if your page is https://www.buymeacoffee.com/survivorpool, this is "survivorpool".
const BUYMEACOFFEE_USERNAME = 'yourusername'

export function Footer() {
  return (
    <footer className="border-t border-gray-200 dark:border-gray-700 py-6 px-4">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-center gap-2 text-sm text-gray-500 dark:text-gray-400">
        <span>Enjoying SurvivorPool?</span>
        <a
          href={`https://www.buymeacoffee.com/${BUYMEACOFFEE_USERNAME}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-full bg-survivor-gold px-4 py-1.5 font-semibold text-survivor-dark shadow-sm transition-colors hover:bg-[#d99400]"
        >
          <span aria-hidden="true">☕</span>
          Buy me a coffee
        </a>
      </div>
    </footer>
  )
}
