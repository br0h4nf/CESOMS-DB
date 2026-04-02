const CURRENT_STUDENT_ID = "90673";

let data = {
  academicTerm: {},
  students: [],
  administrators: [],
  organizations: [],
  organizationOfficers: [],
  memberships: [],
  locations: [],
  categories: [],
  events: [],
  registrations: [],
  attendance: [],
  approvals: [],
  reports: []
};

const state = {
  role: "student",
  search: "",
  category: "all",
  status: "all",
  activeTable: "events",
};

const roleProfiles = {
  student: {
    title: "Student workspace",
    description:
      "Browse upcoming events, register instantly, track your event history, and stay connected to your organizations.",
    primaryAction: "Browse upcoming events",
    secondaryAction: "View my registrations",
    focusTitle: "My student activity",
  },
  officer: {
    title: "Organization officer workspace",
    description:
      "Monitor event performance, registrations, and organization activity from one place.",
    primaryAction: "Review event activity",
    secondaryAction: "View organization roster",
    focusTitle: "Officer operations board",
  },
  admin: {
    title: "University administrator workspace",
    description:
      "Track organization activity, review approvals, and monitor campus engagement.",
    primaryAction: "Review approvals",
    secondaryAction: "View reports",
    focusTitle: "Administrative oversight",
  },
};

const roleButtons = document.getElementById("roleButtons");
const categoryFilter = document.getElementById("categoryFilter");
const statusFilter = document.getElementById("statusFilter");
const searchInput = document.getElementById("searchInput");
const eventsGrid = document.getElementById("eventsGrid");
const eventSummary = document.getElementById("eventSummary");
const heroStats = document.getElementById("heroStats");
const roleTitle = document.getElementById("roleTitle");
const roleDescription = document.getElementById("roleDescription");
const primaryAction = document.getElementById("primaryAction");
const secondaryAction = document.getElementById("secondaryAction");
const pulseCards = document.getElementById("pulseCards");
const entityPills = document.getElementById("entityPills");
const focusTitle = document.getElementById("focusTitle");
const focusCards = document.getElementById("focusCards");
const activityFeed = document.getElementById("activityFeed");
const tableButtons = document.getElementById("tableButtons");
const tableDescription = document.getElementById("tableDescription");
const tableHead = document.getElementById("tableHead");
const tableBody = document.getElementById("tableBody");
const categoryBars = document.getElementById("categoryBars");
const reportCards = document.getElementById("reportCards");
const termLabel = document.getElementById("termLabel");

init();

async function init() {
  await loadData();
  populateFilters();
  bindEvents();
  render();
  setupReveal();
}

async function loadData() {
  try {
    const response = await fetch("/api/dashboard");
    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }
    data = await response.json();

    if (!Array.isArray(data.reports)) {
      data.reports = [];
    }
  } catch (error) {
    console.error("Failed to load dashboard data:", error);
  }
}

async function registerEvent(eventId) {
  try {
    const response = await fetch("/api/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        studentId: CURRENT_STUDENT_ID,
        eventId,
      }),
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || `Register failed with status ${response.status}`);
    }

    alert(
      result.status === "Registered"
        ? "You are registered!"
        : "Event is full. You were added to the waitlist."
    );

    await refreshApp();
  } catch (error) {
    console.error("Registration failed:", error);
    alert(`Registration failed: ${error.message}`);
  }
}

async function cancelRegistration(eventId) {
  try {
    const response = await fetch("/api/cancel-registration", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        studentId: CURRENT_STUDENT_ID,
        eventId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Cancel failed with status ${response.status}`);
    }

    alert("Registration cancelled.");
    await refreshApp();
  } catch (error) {
    console.error("Cancellation failed:", error);
    alert("Could not cancel registration.");
  }
}

async function refreshApp() {
  await loadData();
  populateFilters();
  render();
}

function bindEvents() {
  if (searchInput) {
    searchInput.addEventListener("input", (event) => {
      state.search = event.target.value.trim().toLowerCase();
      renderEvents();
    });
  }

  if (categoryFilter) {
    categoryFilter.addEventListener("change", (event) => {
      state.category = event.target.value;
      renderEvents();
    });
  }

  if (statusFilter) {
    statusFilter.addEventListener("change", (event) => {
      state.status = event.target.value;
      renderEvents();
    });
  }

  if (primaryAction) {
    primaryAction.addEventListener("click", () => {
      scrollToSection("eventExplorer");
    });
  }

  if (secondaryAction) {
    secondaryAction.addEventListener("click", () => {
      if (state.role === "student") {
        scrollToSection("operationsPanel");
      } else {
        scrollToSection("dataPanel");
      }
    });
  }

  document.querySelectorAll("[data-scroll-target]").forEach((button) => {
    button.addEventListener("click", () => {
      scrollToSection(button.dataset.scrollTarget);
    });
  });
}

function populateFilters() {
  if (categoryFilter) {
    const categoryOptions = [
      ["all", "All categories"],
      ...data.categories.map((category) => [category.categoryId, category.categoryName]),
    ];

    categoryFilter.innerHTML = categoryOptions
      .map(([value, label]) => `<option value="${value}">${label}</option>`)
      .join("");
  }

  if (statusFilter) {
    const statuses =
      state.role === "student"
        ? ["Approved", "Scheduled"]
        : state.role === "officer"
        ? ["Approved", "Scheduled", "Submitted"]
        : ["Approved", "Scheduled", "Submitted", "Rejected"];

    const statusOptions = [["all", "All statuses"], ...statuses.map((status) => [status, status])];

    statusFilter.innerHTML = statusOptions
      .map(([value, label]) => `<option value="${value}">${label}</option>`)
      .join("");
  }
}

function render() {
  renderHero();
  renderRoleButtons();
  renderPulse();
  renderEntityPills();
  renderEvents();
  renderFocusCards();
  renderActivityFeed();
  renderTableBrowser();
  renderCategoryBars();
  renderReports();

  if (termLabel) {
    const termName = data.academicTerm?.termName || "Academic term";
    const start = data.academicTerm?.startDate ? formatDate(data.academicTerm.startDate) : "";
    const end = data.academicTerm?.endDate ? formatDate(data.academicTerm.endDate) : "";
    termLabel.textContent = start && end ? `${termName} | ${start} to ${end}` : termName;
  }
}

function renderRoleButtons() {
  if (!roleButtons) return;

  const roles = Object.keys(roleProfiles);

  roleButtons.innerHTML = roles
    .map((role) => {
      const label = role === "admin" ? "Administrator" : capitalize(role);
      const classes = role === state.role ? "role-button is-active" : "role-button";
      return `<button type="button" class="${classes}" data-role="${role}">${label}</button>`;
    })
    .join("");

  roleButtons.querySelectorAll("[data-role]").forEach((button) => {
    button.addEventListener("click", () => {
      state.role = button.dataset.role;
      state.status = "all";
      populateFilters();
      render();
    });
  });
}

function renderHero() {
  if (!roleTitle || !roleDescription || !primaryAction || !secondaryAction || !heroStats) return;

  const profile = roleProfiles[state.role];
  roleTitle.textContent = profile.title;
  roleDescription.textContent = profile.description;
  primaryAction.textContent = profile.primaryAction;
  secondaryAction.textContent = profile.secondaryAction;

  const stats = getRoleStats(state.role);
  heroStats.innerHTML = stats
    .map(
      (stat) => `
        <article class="stat-card">
          <span class="stat-label">${stat.label}</span>
          <strong class="stat-value">${stat.value}</strong>
        </article>
      `
    )
    .join("");
}

function renderPulse() {
  if (!pulseCards) return;

  const studentOpenEvents = data.events.filter((event) =>
    ["Approved", "Scheduled"].includes(event.eventStatus)
  ).length;
  const activeOrgs = data.organizations.filter((org) => org.orgStatus === "Active").length;
  const pendingApprovals = data.approvals.filter((approval) => approval.decisionStatus === "Pending").length;
  const registeredSeats = data.registrations.filter(
    (registration) => registration.registrationStatus === "Registered"
  ).length;

  const cards = [
    { label: "Open student events", value: studentOpenEvents },
    { label: "Active organizations", value: activeOrgs },
    { label: "Pending approvals", value: pendingApprovals },
    { label: "Registered seats", value: registeredSeats },
  ];

  pulseCards.innerHTML = cards
    .map(
      (card) => `
        <article class="pulse-card">
          <span class="pulse-label">${card.label}</span>
          <strong class="pulse-value">${card.value}</strong>
        </article>
      `
    )
    .join("");
}

function renderEntityPills() {
  if (!entityPills) return;

  const entities = [
    ["Students", data.students.length],
    ["Organizations", data.organizations.length],
    ["Events", data.events.length],
    ["Registrations", data.registrations.length],
    ["Attendance", data.attendance.length],
    ["Approvals", data.approvals.length],
  ];

  entityPills.innerHTML = entities
    .map(([label, value]) => `<span class="entity-pill">${label}: ${value}</span>`)
    .join("");
}

function renderEvents() {
  if (!eventsGrid || !eventSummary) return;

  const events = getFilteredEvents();
  eventSummary.textContent = `${events.length} events match the current filters for the ${capitalize(
    state.role
  )} view.`;

  if (!events.length) {
    eventsGrid.innerHTML = `
      <article class="event-card">
        <h4>No matching events</h4>
        <p class="event-meta">Try another category, status, or search term.</p>
      </article>
    `;
    return;
  }

  eventsGrid.innerHTML = events
    .map((event) => {
      const registeredCount = getRegisteredCount(event.eventId);
      const fillRate = event.capacity > 0 ? Math.round((registeredCount / event.capacity) * 100) : 0;
      const location = getLocation(event.locationId);
      const capacityLabel = `${registeredCount}/${event.capacity} seats`;
      const metaTone =
        event.eventStatus === "Rejected" ? "warn" : event.eventStatus === "Submitted" ? "alt" : "";

      const userRegistration = getStudentRegistration(CURRENT_STUDENT_ID, event.eventId);
      const actionHtml =
        state.role === "student" ? renderStudentActionButton(event, userRegistration, registeredCount) : "";

      const registrationBadge = state.role === "student"
        ? `<span class="meta-chip alt">${getStudentEventStateLabel(userRegistration, event, registeredCount)}</span>`
        : "";

      return `
        <article class="event-card">
          <div class="meta-row">
            <span class="meta-chip">${getCategoryName(event.categoryId)}</span>
            <span class="meta-chip ${metaTone}">${event.eventStatus}</span>
            ${registrationBadge}
          </div>
          <div>
            <h4>${event.title}</h4>
            <p class="event-meta">${event.description}</p>
          </div>
          <div class="event-meta">
            <strong>${getOrgName(event.orgId)}</strong><br />
            ${formatDate(event.startDateTime, true)}<br />
            ${location ? `${location.locationName}${location.isVirtual ? " | virtual" : ""}` : "Location unavailable"}
          </div>
          <div class="meta-row">
            <span class="meta-chip alt">${capacityLabel}</span>
            <span class="meta-chip">Fill ${fillRate}%</span>
          </div>
          ${actionHtml}
        </article>
      `;
    })
    .join("");
}

function renderStudentActionButton(event, userRegistration, registeredCount) {
  const isOpenForStudents = ["Approved", "Scheduled"].includes(event.eventStatus);

  if (!isOpenForStudents) {
    return `<div class="meta-row"><span class="meta-chip warn">Not open for registration</span></div>`;
  }

  if (userRegistration && userRegistration.registrationStatus === "Registered") {
    return `
      <div class="action-row">
        <button class="button-solid" type="button" onclick="cancelRegistration('${event.eventId}')">
          Cancel registration
        </button>
      </div>
    `;
  }

  if (userRegistration && userRegistration.registrationStatus === "Waitlisted") {
    return `
      <div class="action-row">
        <button class="button-solid" type="button" onclick="cancelRegistration('${event.eventId}')">
          Leave waitlist
        </button>
      </div>
    `;
  }

  const label = registeredCount >= event.capacity ? "Join waitlist" : "Register";
  return `
    <div class="action-row">
      <button class="button-solid" type="button" onclick="registerEvent('${event.eventId}')">
        ${label}
      </button>
    </div>
  `;
}

function renderFocusCards() {
  if (!focusTitle || !focusCards) return;

  focusTitle.textContent = roleProfiles[state.role].focusTitle;

  const focusData = getFocusData(state.role);
  focusCards.innerHTML = focusData
    .map(
      (card) => `
        <article class="focus-card">
          <span class="focus-label">${card.label}</span>
          <h4>${card.title}</h4>
          ${card.value ? `<strong class="focus-value">${card.value}</strong>` : ""}
          ${
            card.items && card.items.length
              ? `<ul class="focus-list">${card.items.map((item) => `<li>${item}</li>`).join("")}</ul>`
              : `<p class="mini-text">${card.copy || ""}</p>`
          }
        </article>
      `
    )
    .join("");
}

function renderActivityFeed() {
  if (!activityFeed) return;

  const items = getActivityItems(state.role);
  activityFeed.innerHTML = items
    .map(
      (item) => `
        <article class="activity-item">
          <span class="activity-title">${item.title}</span>
          <div class="activity-copy">${item.copy}</div>
        </article>
      `
    )
    .join("");
}

function renderTableBrowser() {
  if (!tableButtons || !tableDescription || !tableHead || !tableBody) return;

  const tableConfig = getTableConfig();

  tableButtons.innerHTML = Object.entries(tableConfig)
    .map(([key, config]) => {
      const classes = key === state.activeTable ? "table-button is-active" : "table-button";
      return `<button type="button" class="${classes}" data-table="${key}">${config.label}</button>`;
    })
    .join("");

  tableButtons.querySelectorAll("[data-table]").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeTable = button.dataset.table;
      renderTableBrowser();
    });
  });

  const activeConfig = tableConfig[state.activeTable];
  if (!activeConfig) return;

  tableDescription.textContent = activeConfig.description;
  tableHead.innerHTML = `<tr>${activeConfig.columns.map((column) => `<th>${column}</th>`).join("")}</tr>`;
  tableBody.innerHTML = activeConfig.rows
    .map((row) => `<tr>${row.map((value) => `<td>${value ?? ""}</td>`).join("")}</tr>`)
    .join("");
}

function renderCategoryBars() {
  if (!categoryBars) return;

  const studentVisibleEvents = data.events.filter((event) => ["Approved", "Scheduled"].includes(event.eventStatus));

  const totals = data.categories.map((category) => {
    const count = studentVisibleEvents.filter((event) => event.categoryId === category.categoryId).length;
    return {
      label: category.categoryName,
      value: count,
      width: studentVisibleEvents.length ? Math.round((count / studentVisibleEvents.length) * 100) : 0,
    };
  });

  categoryBars.innerHTML = totals
    .map(
      (item) => `
        <article class="bar-item">
          <div class="bar-head">
            <span>${item.label}</span>
            <span>${item.value} event${item.value === 1 ? "" : "s"}</span>
          </div>
          <div class="bar-line">
            <div class="bar-fill" style="width: ${item.width}%"></div>
          </div>
        </article>
      `
    )
    .join("");
}

function renderReports() {
  if (!reportCards) return;

  const reports = Array.isArray(data.reports) ? data.reports : [];
  reportCards.innerHTML = reports
    .map(
      (report) => `
        <article class="report-card">
          <span class="report-label">${report.reportType}</span>
          <h4>${report.summary}</h4>
          <div class="report-meta">
            ${formatDate(report.generatedAt, true)} | ${getAdminName(report.generatedByAdminId)}
          </div>
        </article>
      `
    )
    .join("");

  if (!reports.length) {
    reportCards.innerHTML = `
      <article class="report-card">
        <span class="report-label">Reports</span>
        <h4>No reports available yet</h4>
        <div class="report-meta">This section can be powered later by analytics queries.</div>
      </article>
    `;
  }
}

function getTableConfig() {
  return {
    students: {
      label: "STUDENT",
      description: "Core student accounts used for memberships, registrations, and attendance history.",
      columns: ["StudentID", "Name", "Email", "ClassYear", "Major", "AccountStatus"],
      rows: data.students.map((student) => [
        student.studentId,
        `${student.firstName} ${student.lastName}`,
        student.email,
        student.classYear,
        student.major,
        student.accountStatus,
      ]),
    },
    organizations: {
      label: "ORGANIZATION",
      description: "Student organizations with status, contact info, and hosted event ownership.",
      columns: ["OrgID", "OrgName", "Status", "ContactEmail", "Description"],
      rows: data.organizations.map((org) => [
        org.orgId,
        org.orgName,
        org.orgStatus,
        org.contactEmail,
        org.description,
      ]),
    },
    events: {
      label: "EVENT",
      description: "Event records linked to an organization, location, category, and academic term.",
      columns: ["EventID", "Title", "Organization", "Category", "Location", "Status", "Capacity"],
      rows: data.events.map((event) => [
        event.eventId,
        event.title,
        getOrgName(event.orgId),
        getCategoryName(event.categoryId),
        getLocationName(event.locationId),
        event.eventStatus,
        event.capacity,
      ]),
    },
    registrations: {
      label: "REGISTRATION",
      description: "Student-to-event registration records with timing and waitlist visibility.",
      columns: ["Student", "Event", "RegisteredAt", "Status"],
      rows: data.registrations.map((registration) => [
        getStudentName(registration.studentId),
        getEventTitle(registration.eventId),
        registration.registeredAt ? formatDate(registration.registeredAt, true) : "",
        registration.registrationStatus,
      ]),
    },
    approvals: {
      label: "APPROVAL",
      description: "Administrative review data for submitted events and their final decisions.",
      columns: ["Event", "SubmittedBy", "ReviewedBy", "DecisionStatus", "SubmittedAt", "Notes"],
      rows: data.approvals.map((approval) => [
        getEventTitle(approval.eventId),
        getStudentName(approval.submittedByOfficerStudentId),
        approval.reviewedByAdminId ? getAdminName(approval.reviewedByAdminId) : "Pending review",
        approval.decisionStatus,
        approval.submittedAt ? formatDate(approval.submittedAt, true) : "",
        approval.decisionNotes,
      ]),
    },
    attendance: {
      label: "ATTENDANCE",
      description: "Check-in tracking for completed events, recorded by organization officers.",
      columns: ["Student", "Event", "CheckInTime", "AttendanceFlag", "RecordedBy"],
      rows: data.attendance.map((entry) => [
        getStudentName(entry.studentId),
        getEventTitle(entry.eventId),
        entry.checkInTime ? formatDate(entry.checkInTime, true) : "",
        entry.attendanceFlag,
        `${getStudentName(entry.recordedByOfficerStudentId)} / ${getOrgName(entry.recordedByOfficerOrgId)}`,
      ]),
    },
  };
}

function getFilteredEvents() {
  return data.events.filter((event) => {
    const location = getLocationName(event.locationId).toLowerCase();
    const organization = getOrgName(event.orgId).toLowerCase();

    const matchesSearch =
      !state.search ||
      event.title.toLowerCase().includes(state.search) ||
      event.description.toLowerCase().includes(state.search) ||
      location.includes(state.search) ||
      organization.includes(state.search);

    const matchesCategory = state.category === "all" || event.categoryId === state.category;
    const matchesStatus = state.status === "all" || event.eventStatus === state.status;

    if (state.role === "student" && !["Approved", "Scheduled"].includes(event.eventStatus)) {
      return false;
    }

    if (state.role === "officer" && !["Approved", "Scheduled", "Submitted"].includes(event.eventStatus)) {
      return false;
    }

    return matchesSearch && matchesCategory && matchesStatus;
  });
}

function getRoleStats(role) {
  const studentId = CURRENT_STUDENT_ID;

  if (role === "student") {
    const registered = data.registrations.filter(
      (registration) =>
        registration.studentId === studentId && registration.registrationStatus === "Registered"
    ).length;

    const waitlisted = data.registrations.filter(
      (registration) =>
        registration.studentId === studentId && registration.registrationStatus === "Waitlisted"
    ).length;

    const memberships = data.memberships.filter(
      (membership) => membership.studentId === studentId && !membership.leaveDate
    ).length;

    const checkedIn = data.attendance.filter((entry) => entry.studentId === studentId).length;

    return [
      { label: "Registered events", value: registered },
      { label: "Waitlisted events", value: waitlisted },
      { label: "Organization memberships", value: memberships },
      { label: "Events attended", value: checkedIn },
    ];
  }

  if (role === "officer") {
    const officer = data.organizationOfficers.find((entry) => entry.studentId === studentId);
    if (!officer) {
      return [
        { label: "Events under management", value: 0 },
        { label: "Active members", value: 0 },
        { label: "Pending approvals", value: 0 },
        { label: "Registered seats", value: 0 },
      ];
    }

    const orgEvents = data.events.filter((event) => event.orgId === officer.orgId);
    const roster = data.memberships.filter((membership) => membership.orgId === officer.orgId && !membership.leaveDate);
    const pending = data.approvals.filter(
      (approval) =>
        approval.submittedByOfficerOrgId === officer.orgId && approval.decisionStatus === "Pending"
    ).length;

    const seats = data.registrations.filter(
      (registration) =>
        orgEvents.some((event) => event.eventId === registration.eventId) &&
        registration.registrationStatus === "Registered"
    ).length;

    return [
      { label: "Events under management", value: orgEvents.length },
      { label: "Active members", value: roster.length },
      { label: "Pending approvals", value: pending },
      { label: "Registered seats", value: seats },
    ];
  }

  const activeOrgs = data.organizations.filter((org) => org.orgStatus === "Active").length;
  const scheduledEvents = data.events.filter((event) => ["Approved", "Scheduled"].includes(event.eventStatus)).length;
  const pendingApprovals = data.approvals.filter((approval) => approval.decisionStatus === "Pending").length;
  const generatedReports = data.reports.length;

  return [
    { label: "Active organizations", value: activeOrgs },
    { label: "Scheduled events", value: scheduledEvents },
    { label: "Pending approvals", value: pendingApprovals },
    { label: "Generated reports", value: generatedReports },
  ];
}

function getFocusData(role) {
  if (role === "student") {
    const studentId = CURRENT_STUDENT_ID;

    const myRegisteredEvents = data.registrations
      .filter(
        (registration) =>
          registration.studentId === studentId &&
          registration.registrationStatus === "Registered"
      )
      .map((registration) => {
        const event = data.events.find((entry) => entry.eventId === registration.eventId);
        if (!event) return null;

        return {
          title: event.title,
          date: event.startDateTime,
          line: `${event.title} | ${formatDate(event.startDateTime, true)} | ${getOrgName(event.orgId)}`
        };
      })
      .filter(Boolean)
      .sort((a, b) => new Date(a.date) - new Date(b.date));

    const myWaitlistedEvents = data.registrations
      .filter(
        (registration) =>
          registration.studentId === studentId &&
          registration.registrationStatus === "Waitlisted"
      )
      .map((registration) => {
        const event = data.events.find((entry) => entry.eventId === registration.eventId);
        if (!event) return null;

        return `${event.title} | ${formatDate(event.startDateTime, true)} | ${getOrgName(event.orgId)}`;
      })
      .filter(Boolean);

    const nextEvent = myRegisteredEvents.length
      ? myRegisteredEvents[0].line
      : "No upcoming registered events";

    const memberships = data.memberships
      .filter((membership) => membership.studentId === studentId && !membership.leaveDate)
      .map((membership) => `${getOrgName(membership.orgId)} | ${membership.memberRole}`);

    return [
      {
        label: "My next event",
        title: myRegisteredEvents.length ? myRegisteredEvents[0].title : "Nothing scheduled",
        copy: nextEvent,
      },
      {
        label: "Signed up now",
        title: `${myRegisteredEvents.length} registered event${myRegisteredEvents.length === 1 ? "" : "s"}`,
        items: myRegisteredEvents.length
          ? myRegisteredEvents.map((event) => event.line)
          : ["You have not signed up for any events yet"],
      },
      {
        label: "Waitlist and memberships",
        title: `${myWaitlistedEvents.length} waitlisted | ${memberships.length} memberships`,
        items:
          myWaitlistedEvents.length || memberships.length
            ? [
                ...myWaitlistedEvents.map((event) => `Waitlisted | ${event}`),
                ...memberships.map((membership) => `Member | ${membership}`),
              ]
            : ["No waitlisted events or memberships yet"],
      },
    ];
  }

  if (role === "officer") {
    const officer = data.organizationOfficers.find((entry) => entry.studentId === CURRENT_STUDENT_ID);
    if (!officer) {
      return [
        {
          label: "Officer profile",
          title: "No officer assignment found",
          copy: "This student is not currently mapped to an officer record.",
        },
      ];
    }

    const org = getOrg(officer.orgId);
    const orgEvents = data.events
      .filter((event) => event.orgId === officer.orgId)
      .map((event) => `${event.title} | ${event.eventStatus}`);

    const roster = data.memberships
      .filter((membership) => membership.orgId === officer.orgId && !membership.leaveDate)
      .map((membership) => `${getStudentName(membership.studentId)} | ${membership.memberRole}`);

    return [
      {
        label: "Officer profile",
        title: `${getStudentName(officer.studentId)} | ${officer.roleTitle}`,
        copy: `${org ? org.orgName : officer.orgId} is the active organization in this officer view.`,
      },
      {
        label: "Managed event load",
        title: `${orgEvents.length} events in the pipeline`,
        items: orgEvents.length ? orgEvents : ["No events managed yet"],
      },
      {
        label: "Roster preview",
        title: `${roster.length} active members`,
        items: roster.length ? roster : ["No active members found"],
      },
    ];
  }

  const pending = data.approvals
    .filter((approval) => approval.decisionStatus === "Pending")
    .map((approval) => `${getEventTitle(approval.eventId)} | ${approval.decisionNotes}`);

  const orgHealth = data.organizations.map((org) => `${org.orgName} | ${org.orgStatus}`);

  const reportTypes = data.reports.map(
    (report) => `${report.reportType} | ${formatDate(report.generatedAt, true)}`
  );

  return [
    {
      label: "Approval queue",
      title: `${pending.length} submissions need review`,
      items: pending.length ? pending : ["No pending approvals"],
    },
    {
      label: "Organization status",
      title: `${data.organizations.length} tracked organizations`,
      items: orgHealth.length ? orgHealth : ["No organizations found"],
    },
    {
      label: "Reporting stream",
      title: `${data.reports.length} recent reports`,
      items: reportTypes.length ? reportTypes : ["No reports available"],
    },
  ];
}


function getActivityItems(role) {
  if (role === "student") {
    const studentName = getStudentName(CURRENT_STUDENT_ID);
    return [
      {
        title: "My schedule",
        copy: `${studentName} is registered for ${countRegistrationsForStudent(CURRENT_STUDENT_ID)} event(s).`,
      },
      {
        title: "My memberships",
        copy: `${studentName} belongs to ${countMembershipsForStudent(CURRENT_STUDENT_ID)} active organization(s).`,
      },
      {
        title: "Attendance record",
        copy: `${studentName} has ${countAttendanceForStudent(CURRENT_STUDENT_ID)} recorded attendance entry(s).`,
      },
    ];
  }

  const items = [
    {
      title: "Registration opened",
      copy: `Career Lab Live has ${countRegistrationsForEvent("EVT-2405")} registered student(s).`,
    },
    {
      title: "Approval checkpoint",
      copy: `There are ${data.approvals.filter((approval) => approval.decisionStatus === "Pending").length} pending approval request(s).`,
    },
    {
      title: "Attendance captured",
      copy: `Hack Night Studio has ${countAttendanceForEvent("EVT-2401")} attendance record(s).`,
    },
  ];

  if (role === "officer") {
    items.unshift({
      title: "Roster movement",
      copy: `${getOrgName("ORG-ACM")} has ${countMembersForOrg("ORG-ACM")} active member(s).`,
    });
  }

  if (role === "admin") {
    items.unshift({
      title: "System overview",
      copy: `${data.organizations.length} organization(s) and ${data.events.length} event(s) are currently tracked.`,
    });
  }

  return items;
}

function getStudentRegistration(studentId, eventId) {
  return data.registrations.find(
    (registration) =>
      registration.studentId === studentId &&
      registration.eventId === eventId &&
      registration.registrationStatus !== "Cancelled"
  );
}

function getStudentEventStateLabel(userRegistration, event, registeredCount) {
  if (userRegistration?.registrationStatus === "Registered") {
    return "Registered";
  }

  if (userRegistration?.registrationStatus === "Waitlisted") {
    return "Waitlisted";
  }

  if (registeredCount >= event.capacity) {
    return "Full";
  }

  return "Open";
}

function getRegisteredCount(eventId) {
  return data.registrations.filter(
    (registration) =>
      registration.eventId === eventId && registration.registrationStatus === "Registered"
  ).length;
}

function getStudentName(studentId) {
  const student = data.students.find((entry) => entry.studentId === studentId);
  return student ? `${student.firstName} ${student.lastName}` : studentId;
}

function getAdminName(adminId) {
  const admin = data.administrators.find((entry) => entry.adminId === adminId);
  return admin ? `${admin.firstName} ${admin.lastName}` : adminId;
}

function getOrgName(orgId) {
  const org = getOrg(orgId);
  return org ? org.orgName : orgId;
}

function getOrg(orgId) {
  return data.organizations.find((entry) => entry.orgId === orgId);
}

function getCategoryName(categoryId) {
  const category = data.categories.find((entry) => entry.categoryId === categoryId);
  return category ? category.categoryName : categoryId;
}

function getEventTitle(eventId) {
  const event = data.events.find((entry) => entry.eventId === eventId);
  return event ? event.title : eventId;
}

function getLocation(locationId) {
  return data.locations.find((entry) => entry.locationId === locationId);
}

function getLocationName(locationId) {
  const location = getLocation(locationId);
  return location ? location.locationName : locationId;
}

function countRegistrationsForStudent(studentId) {
  return data.registrations.filter(
    (registration) =>
      registration.studentId === studentId &&
      registration.registrationStatus === "Registered"
  ).length;
}

function countMembershipsForStudent(studentId) {
  return data.memberships.filter(
    (membership) => membership.studentId === studentId && !membership.leaveDate
  ).length;
}

function countAttendanceForStudent(studentId) {
  return data.attendance.filter((entry) => entry.studentId === studentId).length;
}

function countRegistrationsForEvent(eventId) {
  return data.registrations.filter(
    (registration) =>
      registration.eventId === eventId &&
      registration.registrationStatus === "Registered"
  ).length;
}

function countAttendanceForEvent(eventId) {
  return data.attendance.filter((entry) => entry.eventId === eventId).length;
}

function countMembersForOrg(orgId) {
  return data.memberships.filter(
    (membership) => membership.orgId === orgId && !membership.leaveDate
  ).length;
}

function formatDate(value, withTime = false) {
  if (!value) return "";

  const formatter = new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    ...(withTime
      ? {
          hour: "numeric",
          minute: "2-digit",
        }
      : {}),
  });

  return formatter.format(parseDateValue(value));
}

function parseDateValue(value) {
  if (!value) return new Date();

  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(year, month - 1, day);
  }

  return new Date(value);
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function scrollToSection(id) {
  document.getElementById(id)?.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
}

function setupReveal() {
  if (!("IntersectionObserver" in window)) {
    document.querySelectorAll(".reveal").forEach((element) => {
      element.classList.add("is-visible");
    });
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
        }
      });
    },
    {
      threshold: 0.15,
    }
  );

  document.querySelectorAll(".reveal").forEach((element) => observer.observe(element));
}