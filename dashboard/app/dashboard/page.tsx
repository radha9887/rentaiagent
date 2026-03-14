"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
export default function DashRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace("/developers"); }, [router]);
  return null;
}
