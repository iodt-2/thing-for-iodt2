import { Outlet } from "react-router-dom";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";
import Footer from "./Footer";
import { Toaster } from "@/components/ui/toaster";
import useSidebarStore from "@/store/useSidebarStore";

const Layout = () => {
  const { isCollapsed } = useSidebarStore();

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className={`flex-1 ${isCollapsed ? "ml-16" : "ml-64"} pt-16 transition-all duration-300`}>
          <div className="p-6 min-h-[calc(100vh-4rem-3.5rem)]">
            <Outlet />
          </div>
          <Footer />
        </main>
      </div>
      <Toaster />
    </div>
  );
};

export default Layout;