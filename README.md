# README #

This is a repository of fiddle tunes with a website for generating set sheets that contain
melody reminders (two measures of each part) and chord charts. There are also recordings
which are linked into the web content.

## Permissions Model

There are four access levels: anonymous visitors, regular logged-in users, editors, and admins.

### Anonymous (not logged in)

Can view all public site content — tune pages, public events, the index, set sheets, PDFs,
and recordings. Cannot create, edit, or delete anything. Cannot add notes. Private events
are hidden unless accessed via a share URL.

### Regular Logged-In Users

**Tunes:** Can create new tunes. The creator becomes the tune's owner and can edit or
delete it. Completed tunes appear on the main index; incomplete tunes are listed only on
the /dev page (but all tunes are accessible by direct URL). Regular users cannot edit or
delete other people's tunes.

**Events:** Can create new events. Events start private. The owner can edit the event
(add/remove/reorder sets, rename, add description, manage co-owners). Private events have
a special share URL (`/ev/<id>`) that grants view access to anyone. To make an event
public, the owner requests publication and an admin must approve it. Once a user has had
3+ events approved, they become a "trusted publisher" and can publish without approval.
Regular users cannot edit or delete other people's events.

**Notes on tunes and events:** Can add personal notes on any tune or event page. On tunes
and events they own, they have a "Make Public" checkbox that lets them share a note with
all visitors. On tunes and events they don't own, their notes are always private.

**Notes on set tunes:** Can add notes on individual tunes within an event's sets. These
notes have no "Make Public" checkbox (to save vertical space on a dense page). Instead,
notes from event owners or co-owners are automatically public; all other users' notes are
private to the note author only.

### Editors

Everything regular users can do, plus:

**Tunes:** Can edit or delete any tune on the site, not just their own. Cannot force-delete
a tune that is in use by an event.

**Events:** Can edit events they own or co-own, but cannot edit arbitrary events. This is
by design — event management beyond one's own events is an admin function.

**Notes:** On tune pages, editors see the "Make Public" checkbox on their notes for all
tunes (since they can edit any tune). On event pages, they see it only for events they
own or co-own. Set-tune notes follow the same rule as regular users — automatically public
only if the editor owns or co-owns the event, private otherwise.

### Admins

Everything editors can do, plus:

**Events:** Can edit or delete any event on the site.

**Admin Area:** Access to the admin page for approving/denying public event requests,
approving/denying editor requests, managing the admin and editor user lists, banning and
unbanning users, clearing caches, rebuilding PDF books, sending notification digests, and
deleting or restoring all content for a user.

**Notes:** Can see and delete any user's notes (public or private). Can toggle public
status on any note.

### Capability System

Roles map to capabilities defined in `tunejam.py`:

| Capability | Regular | Editor | Admin |
|---|---|---|---|
| `kCapManageEvents` (create/manage own events) | Yes | Yes | Yes |
| `kCapEditTunes` (create/edit own tunes) | Yes | Yes | Yes |
| `kCapEditAnyTune` (edit/delete any tune) | No | Yes | Yes |
| `kCapManageAnyEvent` (edit/delete any event, admin powers) | No | No | Yes |
| `kCapDeleteInUse` (force-delete in-use tunes) | No | No | Yes |
| `kCapManageCache` (admin page access) | No | No | Yes |

Access control is enforced server-side on all data-modifying routes. UI elements (edit
buttons, checkboxes, forms) are also conditionally rendered based on the same checks, but
the server never relies solely on the UI for security.
