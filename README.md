# Forum

A PyGDO forum with nested boards, discussion threads and posts. A data model
for post likes exists; its user-facing voting workflow is not implemented yet.

# Forum (For Humans)

Installation creates a public root board named `forum` if it does not already
exist. Running the seed again preserves existing boards and discussions.
When Forum is selected as the site's main module, its root board is the home page.

Boards organize discussions into a tree. A board can require a permission;
its accessible threads contain posts and can be published as RSS.
The board list omits child boards the current viewer cannot access.
Board selector choices are refreshed when permissions or tree placement change.
The sidebar link is also hidden if the viewer cannot access the root board.
Its tree boundaries are read from storage, so a cached board does not leave
the child list stale after another process moves boards.
Board access checks consult the current stored permission, including when a
previously loaded board object is still cached.
Board-dependent methods recheck their specific board on every invocation; a
previously allowed method call does not grant access to another board.
Unknown board IDs or names are rejected without rendering a server error.
Thread access checks use its current stored board, including after a move.
Parent lookup also reads current tree bounds, including after a rollback.
Tracked cache entries changed during a rolled-back transaction are evicted
before subsequent lookups; callers must refresh object references they already hold.
Thread selector choices and name-search suggestions omit inaccessible discussions;
choices are refreshed when reused after permission changes. Direct ID routes
still enforce the current board permission.
Board statistics count threads and replies directly in each board, and the
last-post date reflects the latest post in that board.
Board administration links are shown to staff; the new-thread link is shown
to authenticated users when thread creation is enabled for the board.
Reply counts exclude the thread's opening post and cannot be negative.
Thread records are fetched without object caching so their computed reply
counts reflect newly added posts on the next listing.

## Methods

- `forum.forum` displays a board, its direct child boards and its threads;
  `forum.board` displays a board and its threads, while `forum.boards` lists
  its direct child boards and available actions. A child board links back to
  its parent when the current viewer is allowed to read that parent.
- `threads` and `thread` display threads and their posts.
  In text and chat lists, boards and threads show their stable IDs so they can
  be selected in subsequent commands.
  The thread title remains visible even when it contains no posts.
  The thread list shows the number of replies, excluding the opening post.
  Thread posts show their author and message in text/chat output as well as in
  web cards without changing their stored content or edit timestamp. The
  last-post link opens the last page at the matching post; the thread view
  links back to its current board.
- `new_thread` and `add_thread` provide thread creation entry points.
  `add_thread` is a chat/CLI command, not an HTTP endpoint; web users use the
  CSRF-protected `new_thread` form.
  Thread and opening post are written in one method transaction, so an error
  creating the post rolls the thread back as well.
  Creation requires an authenticated user, access to the chosen board and a
  board with thread creation enabled; these conditions also apply to direct
  requests, not only the navigation button. The creation selector omits boards
  the current user cannot access. After creation the web form links to the new
  thread. Chat example: `$forum.add_thread --board=forum "Chat topic" Hello from chat`.
- `forum.reply` lets an authenticated user reply to a thread on a board they
  may access; the thread view links to the reply form. The stored post belongs
  to the current user and thread, and the success view links to the new post
  on its thread page. In CLI mode its named fields include `thread`,
  `post_message_input` and `post_message_editor`.
  Example: `$forum.reply --thread=1 --post_message_input="Hello!" --post_message_editor=html`.
- `board_crud` and `thread_crud` provide administrative editing interfaces;
  both recheck staff permission. Ordinary thread creation uses `new_thread`
  or `add_thread` and includes an opening post. Staff can enable or disable
  new threads when creating or editing a board; existing threads remain readable.
  Thread administration can update the title and move a thread to another board.
  Staff can open this administration from the thread view.
  Deleting a thread marks it with `GDT_Deleted`, preserving its posts and likes;
  the edit form explains this. Deleted threads are excluded from ordinary
  lists, selectors, direct views, RSS and board counts. The deletion shares the
  method transaction and is rolled back if the owning method reports an error.
  Bulk deletion remains a hard delete. Staff restoration and individual post
  deletion need their own specified interfaces; do not assume they exist.
  It can also create an empty thread without an opening post; use `new_thread`
  or `add_thread` when the opening message should be created together with it.
  Create, update and delete actions show human-readable confirmation messages.
  Board deletion is limited to empty non-root boards; boards containing child
  boards or threads must be emptied first. Tree mutations use database row
  locks within the caller's transaction; a removed board cannot receive a new
  child through the board creation API. When staff select a parent, the move
  compares it with the locked current tree, not a cached parent. The parent
  selector excludes the board and its descendants for names as well as IDs;
  an invalid parent rejects the edit instead of saving only its other fields.
  A missing edit target is rejected instead of displaying a creation form.
- `forum.rss` provides an RSS feed filtered by board permission.
  The most recent 20 accessible posts are selected after filtering; each post
  has its own stable, server-scoped feed identifier and links to its page and
  post anchor. Its description contains the post as escaped plain text;
  generating the feed does not update the post or its edited timestamp.
  The web feed is available at `forum.rss.rss` and linked from the forum view.

## GDTs

`GDT_ForumBoard` and its `GDT_Board` alias select a board; `GDT_Thread`
selects a thread.

## GDOs

`GDO_ForumBoard`, `GDO_ForumThread` and `GDO_ForumPost` store the forum;
`GDO_ForumLikes` records likes on posts.

Editing or deleting individual posts is not currently available through a
forum method; thread and board administration are separate staff workflows.

# Forum (For ALs)

The module depends on `table`, `message` and `likes`; its `forum_dislikes` setting
defaults to enabled but does not currently expose a dislike workflow. The
shared likes table presently accepts only values 0 and 1. Installation
delegates to `ForumInstall`.

## Methods

The `forum`, `board`, `boards`, `threads`, `thread`, `new_thread`, `reply`,
`add_thread`, `board_crud`, `thread_crud` and `rss` method classes live in
`method/`. Board and thread views check the selected board's permission;
the RSS method filters inaccessible boards.
Reply creation requires authentication, checks the target board's permission
before rendering or saving, validates the message and associates the post with
the authenticated user rather than a client-supplied author.
Web forms that create or modify forum records include PyGDO's CSRF field.
HTTP GET renders these forms only; mutations require POST and its transaction.

## GDTs

`GDT_ForumBoard` and `GDT_Thread` are object selectors for their respective
tables; `GDT_Board` aliases the board selector.

## GDOs

`GDO_ForumBoard` uses `GDT_Tree` nested-set bounds and provides child creation
and subtree moves. `GDO_ForumThread` belongs to a board and exposes post
counts; `GDO_ForumPost` belongs to a thread, holds the message and author/edit
metadata, and uses `GDO_ForumLikes` as the storage model for future voting.
There is currently no forum method or post-card control for casting a vote.

## Open questions

- Should post voting support both likes and dislikes? The shared storage model
  currently supports only non-negative values.
- Who may edit or delete an individual post, and how should that appear in the
  discussion?
