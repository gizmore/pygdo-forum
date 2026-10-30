# Forum

A PyGDO forum with nested boards, discussion threads, posts and post likes.

# Forum (For Humans)

Boards organize discussions into a tree. A board can require a permission;
its accessible threads contain posts and can be published as RSS.

## Methods

- `forum`, `board` and `boards` display a board and its children.
- `threads` and `thread` display threads and their posts.
- `new_thread` and `add_thread` provide thread creation entry points.
- `board_crud` and `thread_crud` provide editing interfaces; board management
  requires staff permission.
- `forum.rss` provides an RSS feed filtered by board permission.

## GDTs

`GDT_ForumBoard` and its `GDT_Board` alias select a board; `GDT_Thread`
selects a thread.

## GDOs

`GDO_ForumBoard`, `GDO_ForumThread` and `GDO_ForumPost` store the forum;
`GDO_ForumLikes` records likes on posts.

# Forum (For ALs)

The module depends on `table` and `message`; its `forum_dislikes` setting
defaults to enabled. Installation delegates to `ForumInstall`.

## Methods

The `forum`, `board`, `boards`, `threads`, `thread`, `new_thread`,
`add_thread`, `board_crud`, `thread_crud` and `rss` method classes live in
`method/`. Board and thread views check the selected board's permission;
the RSS method filters inaccessible boards.

## GDTs

`GDT_ForumBoard` and `GDT_Thread` are object selectors for their respective
tables; `GDT_Board` aliases the board selector.

## GDOs

`GDO_ForumBoard` uses `GDT_Tree` nested-set bounds and provides child creation
and subtree moves. `GDO_ForumThread` belongs to a board and exposes post
counts; `GDO_ForumPost` belongs to a thread, holds the message and author/edit
metadata, and uses `GDO_ForumLikes` for likes.

## Open questions

- Which additional forum workflows should be specified next?
