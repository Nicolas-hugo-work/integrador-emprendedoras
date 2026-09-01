# Graph Report - .  (2026-08-31)

## Corpus Check
- Corpus is ~33,029 words - fits in a single context window. You may not need a graph.

## Summary
- 945 nodes · 3515 edges · 60 communities (50 shown, 10 thin omitted)
- Extraction: 46% EXTRACTED · 54% INFERRED · 0% AMBIGUOUS · INFERRED: 1887 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Backend Configuration|Backend Configuration]]
- [[_COMMUNITY_SQLAlchemy Admin Models|SQLAlchemy Admin Models]]
- [[_COMMUNITY_Backend Package|Backend Package]]
- [[_COMMUNITY_API Contracts|API Contracts]]
- [[_COMMUNITY_Backend API Authorization|Backend API Authorization]]
- [[_COMMUNITY_Domain Rules|Domain Rules]]
- [[_COMMUNITY_Backend Package Metadata|Backend Package Metadata]]
- [[_COMMUNITY_Schema Export|Schema Export]]
- [[_COMMUNITY_Static Schema Tests|Static Schema Tests]]
- [[_COMMUNITY_Formatter Configuration|Formatter Configuration]]
- [[_COMMUNITY_Oxc Lint Configuration|Oxc Lint Configuration]]
- [[_COMMUNITY_Frontend Authentication|Frontend Authentication]]
- [[_COMMUNITY_App Layout PWA|App Layout PWA]]
- [[_COMMUNITY_Component Configuration|Component Configuration]]
- [[_COMMUNITY_Accordion UI|Accordion UI]]
- [[_COMMUNITY_Alert Dialog UI|Alert Dialog UI]]
- [[_COMMUNITY_Alert UI|Alert UI]]
- [[_COMMUNITY_UI Primitives Utilities|UI Primitives Utilities]]
- [[_COMMUNITY_Attachment UI|Attachment UI]]
- [[_COMMUNITY_Chat Bubble UI|Chat Bubble UI]]
- [[_COMMUNITY_Button Group Items|Button Group Items]]
- [[_COMMUNITY_Buttons Calendar Messages|Buttons Calendar Messages]]
- [[_COMMUNITY_Carousel UI|Carousel UI]]
- [[_COMMUNITY_Chart UI|Chart UI]]
- [[_COMMUNITY_Combobox UI|Combobox UI]]
- [[_COMMUNITY_Command Palette UI|Command Palette UI]]
- [[_COMMUNITY_Context Menu UI|Context Menu UI]]
- [[_COMMUNITY_Drawer UI|Drawer UI]]
- [[_COMMUNITY_Dropdown Menu UI|Dropdown Menu UI]]
- [[_COMMUNITY_Empty State UI|Empty State UI]]
- [[_COMMUNITY_Form Field UI|Form Field UI]]
- [[_COMMUNITY_Marker UI|Marker UI]]
- [[_COMMUNITY_Navigation Menu UI|Navigation Menu UI]]
- [[_COMMUNITY_Popover UI|Popover UI]]
- [[_COMMUNITY_Responsive Sheet UI|Responsive Sheet UI]]
- [[_COMMUNITY_Tabs UI|Tabs UI]]
- [[_COMMUNITY_Toggle UI|Toggle UI]]
- [[_COMMUNITY_Next.js Configuration|Next.js Configuration]]
- [[_COMMUNITY_Frontend Dependencies|Frontend Dependencies]]
- [[_COMMUNITY_Service Worker Shell|Service Worker Shell]]
- [[_COMMUNITY_TypeScript Configuration|TypeScript Configuration]]
- [[_COMMUNITY_Vite Local Configuration|Vite Local Configuration]]
- [[_COMMUNITY_System Architecture Auth|System Architecture Auth]]
- [[_COMMUNITY_RAG Research Models|RAG Research Models]]
- [[_COMMUNITY_Frontend PWA Architecture|Frontend PWA Architecture]]
- [[_COMMUNITY_Application Logo|Application Logo]]
- [[_COMMUNITY_Backend Security Architecture|Backend Security Architecture]]
- [[_COMMUNITY_Password Hashing|Password Hashing]]
- [[_COMMUNITY_Token Hashing|Token Hashing]]
- [[_COMMUNITY_Next.js Agent Docs|Next.js Agent Docs]]
- [[_COMMUNITY_Test User Seeder|Test User Seeder]]

## God Nodes (most connected - your core abstractions)
1. `cn()` - 343 edges
2. `DB` - 85 edges
3. `CurrentUser` - 78 edges
4. `Base` - 64 edges
5. `User` - 63 edges
6. `UUIDPrimaryKeyMixin` - 63 edges
7. `TimestampMixin` - 63 edges
8. `date` - 61 edges
9. `DateTime6` - 61 edges
10. `Business` - 60 edges

## Surprising Connections (you probably didn't know these)
- `Business` --shares_data_with--> `Formalization Route`  [EXTRACTED]
  backend/app/models/business.py → C:/proyecto-integrador/backend/app/models/business.py
- `Source` --conceptually_related_to--> `AI Run`  [INFERRED]
  backend/app/models/rag.py → C:/proyecto-integrador/backend/app/models/conversation.py
- `Safe RAG Assistant Query` --implements--> `Safe Evidence-Grounded RAG`  [INFERRED]
  C:/proyecto-integrador/backend/app/main.py → C:/proyecto-integrador/README.md
- `HTTPAuthorizationCredentials` --uses--> `User`  [INFERRED]
  backend/app/dependencies.py → backend/app/models/identity.py
- `Depends` --uses--> `User`  [INFERRED]
  backend/app/dependencies.py → backend/app/models/identity.py

## Import Cycles
- 1-file cycle: `backend/app/domain_rules.py -> backend/app/domain_rules.py`
- 1-file cycle: `backend/app/main.py -> backend/app/main.py`
- 1-file cycle: `backend/app/tasks.py -> backend/app/tasks.py`

## Hyperedges (group relationships)
- **Safe RAG Publication and Retrieval Pipeline** — readme_safe_rag, main_source_curation, main_assistant_query, security_text_encryption [INFERRED 0.90]
- **Authenticated Frontend Experience** — page_home_dashboard, app_shell_component, assistant_page, api_request [INFERRED 0.88]
- **Authentication and Session Bootstrap** — login_page, register_page, api_request, api_token_pair, api_save_tokens [EXTRACTED 1.00]
- **RAG Answer Trace** — conversation_message, conversation_ai_run, conversation_ai_retrieval, rag_source_chunk_embedding, conversation_message_citation [EXTRACTED 1.00]
- **User Business Context** — identity_user, business_business, finance_financial_movement, conversation_conversation [EXTRACTED 1.00]
- **Docker Application Stack** — docker_compose_mariadb, docker_compose_backend, docker_compose_frontend [EXTRACTED 1.00]
- **Pila de esquema y contratos del backend Kawsay** — backend_readme_sqlalchemy_models, backend_readme_api_contracts, backend_readme_alembic_initial_migration, backend_readme_schema_export [INFERRED 0.80]
- **Controles de seguridad y privacidad de Kawsay** — backend_readme_argon2id, backend_readme_hashed_tokens, backend_readme_encrypted_sensitive_text, backend_readme_object_storage, backend_readme_data_retention, backend_readme_append_only_audit, backend_readme_private_conversations [EXTRACTED 1.00]

## Communities (60 total, 10 thin omitted)

### Community 11 - "Backend Configuration"
Cohesion: 0.13
Nodes (14): Settings, BaseSettings, get_settings(), get_db(), Session, utc_now(), purge_expired_sessions(), purge_audio_metadata() (+6 more)

### Community 3 - "SQLAlchemy Admin Models"
Cohesion: 0.14
Nodes (42): SecurityAlert, SystemSetting, BackgroundJob, EvaluationSet, EvaluationCase, EvaluationRun, EvaluationResult, ResearchParticipant (+34 more)

### Community 0 - "API Contracts"
Cohesion: 0.34
Nodes (88): ContactRegistration, BaseModel, VerifyContactRequest, LoginRequest, RefreshRequest, TokenPair, RegistrationResult, UserView (+80 more)

### Community 2 - "Backend API Authorization"
Cohesion: 0.10
Nodes (51): get_current_user(), HTTPAuthorizationCredentials, Depends, bearer, User, utc_now(), normalize_contact(), write_audit() (+43 more)

### Community 16 - "Domain Rules"
Cohesion: 0.19
Nodes (12): validate_transfer(), movement_balance_effect(), Decimal, calculate_suggested_price(), validate_normative_response(), audio_purge_deadline(), datetime, account_purge_deadline() (+4 more)

### Community 34 - "Formatter Configuration"
Cohesion: 0.33
Nodes (5): $schema, singleQuote, printWidth, sortPackageJson, ignorePatterns

### Community 7 - "Oxc Lint Configuration"
Cohesion: 0.06
Nodes (33): $schema, plugins, categories, correctness, env, builtin, browser, node (+25 more)

### Community 4 - "Frontend Authentication"
Cohesion: 0.07
Nodes (32): Result, links, AppShell(), AuthFrame(), Business, Business, Category, Movement (+24 more)

### Community 28 - "App Layout PWA"
Cohesion: 0.29
Nodes (5): geistSans, geistMono, metadata, viewport, PwaRegister()

### Community 12 - "Component Configuration"
Cohesion: 0.09
Nodes (21): $schema, style, rsc, tsx, tailwind, config, css, baseColor (+13 more)

### Community 1 - "Accordion UI"
Cohesion: 0.05
Nodes (59): Accordion(), AccordionItem(), AccordionTrigger(), AccordionContent(), Avatar(), AvatarImage(), AvatarFallback(), AvatarBadge() (+51 more)

### Community 24 - "Alert Dialog UI"
Cohesion: 0.15
Nodes (9): AlertDialogOverlay(), AlertDialogContent(), AlertDialogHeader(), AlertDialogFooter(), AlertDialogMedia(), AlertDialogTitle(), AlertDialogDescription(), AlertDialogAction() (+1 more)

### Community 36 - "Alert UI"
Cohesion: 0.40
Nodes (5): alertVariants, Alert(), AlertTitle(), AlertDescription(), AlertAction()

### Community 9 - "UI Primitives Utilities"
Cohesion: 0.06
Nodes (17): AspectRatio(), badgeVariants, Badge(), Checkbox(), HoverCardContent(), InputOTP(), InputOTPGroup(), InputOTPSlot() (+9 more)

### Community 26 - "Attachment UI"
Cohesion: 0.20
Nodes (11): attachmentVariants, Attachment(), attachmentMediaVariants, AttachmentMedia(), AttachmentContent(), AttachmentTitle(), AttachmentDescription(), AttachmentActions() (+3 more)

### Community 31 - "Chat Bubble UI"
Cohesion: 0.38
Nodes (6): BubbleGroup(), bubbleVariants, Bubble(), BubbleContent(), bubbleReactionsVariants, BubbleReactions()

### Community 17 - "Button Group Items"
Cohesion: 0.13
Nodes (17): buttonGroupVariants, ButtonGroup(), ButtonGroupText(), ButtonGroupSeparator(), ItemGroup(), ItemSeparator(), itemVariants, Item() (+9 more)

### Community 6 - "Buttons Calendar Messages"
Cohesion: 0.07
Nodes (23): buttonVariants, Button(), Calendar(), CalendarDayButton(), MessageScroller(), MessageScrollerViewport(), MessageScrollerContent(), MessageScrollerItem() (+15 more)

### Community 22 - "Carousel UI"
Cohesion: 0.19
Nodes (13): CarouselApi, UseCarouselParameters, CarouselOptions, CarouselPlugin, CarouselProps, CarouselContextProps, CarouselContext, useCarousel() (+5 more)

### Community 25 - "Chart UI"
Cohesion: 0.18
Nodes (10): THEMES, INITIAL_DIMENSION, TooltipNameType, ChartConfig, ChartContextProps, ChartContext, useChart(), ChartContainer() (+2 more)

### Community 10 - "Combobox UI"
Cohesion: 0.09
Nodes (23): ComboboxTrigger(), ComboboxClear(), ComboboxInput(), ComboboxContent(), ComboboxList(), ComboboxItem(), ComboboxGroup(), ComboboxLabel() (+15 more)

### Community 15 - "Command Palette UI"
Cohesion: 0.12
Nodes (16): Command(), CommandDialog(), CommandInput(), CommandList(), CommandEmpty(), CommandGroup(), CommandSeparator(), CommandItem() (+8 more)

### Community 20 - "Context Menu UI"
Cohesion: 0.12
Nodes (9): ContextMenuTrigger(), ContextMenuContent(), ContextMenuLabel(), ContextMenuItem(), ContextMenuSubTrigger(), ContextMenuCheckboxItem(), ContextMenuRadioItem(), ContextMenuSeparator() (+1 more)

### Community 21 - "Drawer UI"
Cohesion: 0.14
Nodes (10): DrawerContextProps, DrawerContext, useDrawer(), DrawerOverlay(), DrawerSwipeHandle(), DrawerContent(), DrawerHeader(), DrawerFooter() (+2 more)

### Community 8 - "Dropdown Menu UI"
Cohesion: 0.09
Nodes (26): DropdownMenu(), DropdownMenuPortal(), DropdownMenuTrigger(), DropdownMenuContent(), DropdownMenuGroup(), DropdownMenuLabel(), DropdownMenuItem(), DropdownMenuSub() (+18 more)

### Community 29 - "Empty State UI"
Cohesion: 0.29
Nodes (7): Empty(), EmptyHeader(), emptyMediaVariants, EmptyMedia(), EmptyTitle(), EmptyDescription(), EmptyContent()

### Community 23 - "Form Field UI"
Cohesion: 0.16
Nodes (12): FieldSet(), FieldLegend(), FieldGroup(), fieldVariants, Field(), FieldContent(), FieldLabel(), FieldTitle() (+4 more)

### Community 39 - "Marker UI"
Cohesion: 0.50
Nodes (4): markerVariants, Marker(), MarkerIcon(), MarkerContent()

### Community 27 - "Navigation Menu UI"
Cohesion: 0.22
Nodes (9): NavigationMenu(), NavigationMenuList(), NavigationMenuItem(), navigationMenuTriggerStyle, NavigationMenuTrigger(), NavigationMenuContent(), NavigationMenuPositioner(), NavigationMenuLink() (+1 more)

### Community 32 - "Popover UI"
Cohesion: 0.29
Nodes (4): PopoverContent(), PopoverHeader(), PopoverTitle(), PopoverDescription()

### Community 5 - "Responsive Sheet UI"
Cohesion: 0.06
Nodes (39): Sheet(), SheetOverlay(), SheetContent(), SheetHeader(), SheetFooter(), SheetTitle(), SheetDescription(), SidebarContextProps (+31 more)

### Community 37 - "Tabs UI"
Cohesion: 0.40
Nodes (5): Tabs(), tabsListVariants, TabsList(), TabsTrigger(), TabsContent()

### Community 33 - "Toggle UI"
Cohesion: 0.43
Nodes (5): ToggleGroupContext, ToggleGroup(), ToggleGroupItem(), toggleVariants, Toggle()

### Community 13 - "Frontend Dependencies"
Cohesion: 0.10
Nodes (20): name, version, private, scripts, dev, build, start, lint (+12 more)

### Community 14 - "TypeScript Configuration"
Cohesion: 0.10
Nodes (20): compilerOptions, target, lib, allowJs, skipLibCheck, strict, noEmit, esModuleInterop (+12 more)

### Community 19 - "System Architecture Auth"
Cohesion: 0.20
Nodes (18): Application Settings, SQLAlchemy Persistence Layer, Kawsay FastAPI Application, Authentication and Session Flow, Business Finance Flow, Safe RAG Assistant Query, Consent Export and Deletion Flow, RAG Source Curation Flow (+10 more)

### Community 30 - "RAG Research Models"
Cohesion: 0.38
Nodes (7): Formalization Route, AI Run, AI Retrieval, Message Citation, Source Version, Source Chunk, Source Chunk Embedding

### Community 41 - "Frontend PWA Architecture"
Cohesion: 0.67
Nodes (4): Root Layout, PwaRegister Component, Browser Service Worker Registration, Kawsay PWA Frontend

### Community 18 - "Backend Security Architecture"
Cohesion: 0.12
Nodes (19): Backend Kawsay, MariaDB 11.8 LTS, Modelos SQLAlchemy por dominio, Contratos Pydantic y OpenAPI, MigraciÃ³n Alembic inicial reversible, BÃºsqueda vectorial con distancia coseno, Control de acceso RBAC, Trazabilidad y consulta segura RAG (+11 more)

### Community 40 - "Next.js Agent Docs"
Cohesion: 0.50
Nodes (4): Reglas de agente para Next.js, DocumentaciÃ³n incluida de Next.js, Generador de archivos de agente de Next.js, Referencia de CLAUDE.md a AGENTS.md

### Community 42 - "Test User Seeder"
Cohesion: 0.67
Nodes (3): seed_test_users(), main(), Crea cuentas locales de prueba, una por cada rol del sistema.

## Knowledge Gaps
- **141 isolated node(s):** `Session`, `pwa-autonomia-backend`, `$schema`, `singleQuote`, `printWidth` (+136 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `cn()` connect `Accordion UI` to `Responsive Sheet UI`, `Buttons Calendar Messages`, `Dropdown Menu UI`, `UI Primitives Utilities`, `Combobox UI`, `Command Palette UI`, `Button Group Items`, `Context Menu UI`, `Drawer UI`, `Carousel UI`, `Form Field UI`, `Alert Dialog UI`, `Chart UI`, `Attachment UI`, `Navigation Menu UI`, `Empty State UI`, `Chat Bubble UI`, `Popover UI`, `Toggle UI`, `Alert UI`, `Tabs UI`, `Marker UI`?**
  _High betweenness centrality (0.198) - this node is a cross-community bridge._
- **Why does `DateTime6` connect `SQLAlchemy Admin Models` to `API Contracts`?**
  _High betweenness centrality (0.006) - this node is a cross-community bridge._
- **Why does `DB` connect `Backend API Authorization` to `API Contracts`?**
  _High betweenness centrality (0.005) - this node is a cross-community bridge._
- **Are the 57 inferred relationships involving `DB` (e.g. with `ContactRegistration` and `VerifyContactRequest`) actually correct?**
  _`DB` has 57 INFERRED edges - model-reasoned connections that need verification._
- **Are the 57 inferred relationships involving `CurrentUser` (e.g. with `ContactRegistration` and `VerifyContactRequest`) actually correct?**
  _`CurrentUser` has 57 INFERRED edges - model-reasoned connections that need verification._
- **Are the 62 inferred relationships involving `Base` (e.g. with `AuditEvent` and `SecurityAlert`) actually correct?**
  _`Base` has 62 INFERRED edges - model-reasoned connections that need verification._
- **Are the 57 inferred relationships involving `User` (e.g. with `ContactRegistration` and `VerifyContactRequest`) actually correct?**
  _`User` has 57 INFERRED edges - model-reasoned connections that need verification._