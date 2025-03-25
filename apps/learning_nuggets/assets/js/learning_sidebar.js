document.addEventListener('DOMContentLoaded', function () {
  const toggleButton = document.getElementById('learning-toggle')
  const sidebar = document.getElementById('learning-sidebar')
  const closeButton = document.getElementById('learning-close')
  const sidebarContent = document.getElementById('learning-content')
  const originalUrl = window.location.href

  // Toggle sidebar
  toggleButton.addEventListener('click', function (e) {
    e.preventDefault()
    sidebar.classList.add('active')

    if (!sidebarContent.innerHTML.trim()) {
      loadContent('/learning-center/')
    }
  })

  // Close sidebar and reset URL
  closeButton.addEventListener('click', function (e) {
    e.preventDefault()
    sidebar.classList.remove('active')
    window.history.pushState(null, '', originalUrl)
  })

  // Handle clicks inside the sidebar content
  sidebarContent.addEventListener('click', function (e) {
    const link = e.target.closest('a[data-sidebar]')
    if (link) {
      e.preventDefault()
      loadContent(link.getAttribute('href'))
    }
  })

  // Load content into sidebar via AJAX
  function loadContent (url) {
    fetch(url, {
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
      }
    })
      .then(response => response.text())
      .then(html => {
        sidebarContent.innerHTML = html
        // Update URL without page reload
        window.history.pushState({ sidebarUrl: url }, '', url)
      })
      .catch(error => {
        console.error('Error loading content:', error)
        sidebarContent.innerHTML = '<p>Failed to load content. Please try again.</p>'
      })
  }

  // Handle browser back/forward buttons
  window.addEventListener('popstate', function (event) {
    if (event.state && event.state.sidebarUrl) {
      loadContent(event.state.sidebarUrl)
      sidebar.classList.add('active')
    }
  })
})
