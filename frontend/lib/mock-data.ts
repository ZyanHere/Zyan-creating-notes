export type Project = {
  name: string;
  description: string;
  workstreamCount: number;
  artifactCount: number;
  updatedLabel: string;
  accent: string;
  topicTag: string;
};

export type Template = {
  name: string;
  description: string;
  emphasis: string;
};

export type RecentActivityItem = {
  title: string;
  project: string;
  when: string;
  type: "generated" | "updated" | "created";
};

export const projects: Project[] = [
  {
    name: "Generative AI",
    description: "Research, revision, and interview preparation",
    workstreamCount: 3,
    artifactCount: 12,
    updatedLabel: "Updated 2h ago",
    accent: "from-cyan-500 to-sky-600",
    topicTag: "AI Systems",
  },
  {
    name: "DSA",
    description: "Notes and interview preparation",
    workstreamCount: 4,
    artifactCount: 18,
    updatedLabel: "Updated yesterday",
    accent: "from-amber-500 to-orange-600",
    topicTag: "Interview Prep",
  },
  {
    name: "Electrical Machines",
    description: "B.Tech Semester 4",
    workstreamCount: 2,
    artifactCount: 6,
    updatedLabel: "Updated 3 days ago",
    accent: "from-emerald-500 to-teal-600",
    topicTag: "Engineering",
  },
  {
    name: "English BA 2nd Semester - Paper 2",
    description: "Literary notes, themes, and revision",
    workstreamCount: 3,
    artifactCount: 9,
    updatedLabel: "Updated 5 days ago",
    accent: "from-fuchsia-500 to-pink-600",
    topicTag: "Humanities",
  },
  {
    name: "Operating Systems",
    description: "Concept notes, quick revision, and viva prep",
    workstreamCount: 3,
    artifactCount: 14,
    updatedLabel: "Updated 1 week ago",
    accent: "from-violet-500 to-indigo-600",
    topicTag: "Computer Science",
  },
  {
    name: "GATE Mathematics",
    description: "Formula sheets, worked examples, and practice notes",
    workstreamCount: 4,
    artifactCount: 16,
    updatedLabel: "Updated 2 weeks ago",
    accent: "from-rose-500 to-red-600",
    topicTag: "Competitive Exam",
  },
];

export const templates: Template[] = [
  {
    name: "Visual",
    description: "Flows, diagrams, and concept mapping.",
    emphasis: "Best for complex systems and relationships.",
  },
  {
    name: "Quick",
    description: "Dense summaries built for speed.",
    emphasis: "Best for revision under time pressure.",
  },
  {
    name: "Theory",
    description: "Long-form explanation with conceptual depth.",
    emphasis: "Best for understanding first principles.",
  },
  {
    name: "Q&A",
    description: "Prompts, answers, traps, and follow-ups.",
    emphasis: "Best for interviews, viva, and active recall.",
  },
  {
    name: "Comprehensive",
    description: "Theory, examples, exercises, and supporting material.",
    emphasis: "Best for full-topic notes.",
  },
  {
    name: "Adaptive",
    description: "System-chosen balance based on topic and purpose.",
    emphasis: "Best when the user wants recommendations.",
  },
];

export const recentActivity: RecentActivityItem[] = [
  {
    title: "Generated Quick Revision",
    project: "Generative AI",
    when: "20 minutes ago",
    type: "generated",
  },
  {
    title: "Updated Research Notes",
    project: "DSA",
    when: "Today",
    type: "updated",
  },
  {
    title: "Created Project",
    project: "Electrical Machines",
    when: "Yesterday",
    type: "created",
  },
  {
    title: "Expanded Module Plan",
    project: "Operating Systems",
    when: "2 days ago",
    type: "updated",
  },
];
