import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AX Agent Factory · SoloOS",
  description: "Employee Workbench for governed SoloOS agent creation, approval, and launch.",
};

export default function AgentFactoryLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
