"use client";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/common";
import { ParentForm } from "@/components/parent-form";
import { post } from "@/lib/api";
import type { Parent } from "@/lib/types";

export default function NewParent() {
  const router = useRouter();
  return (
    <>
      <PageHeader title="Add a parent" description="After you add the profile, our team will record your parent’s informed agreement before services can begin." />
      <ParentForm showRelationship submitLabel="Save parent" onSubmit={async (v) => { const p = await post<Parent>("/portal/parents", v); router.push(`/portal/parents/${p.id}`); }} />
    </>
  );
}
