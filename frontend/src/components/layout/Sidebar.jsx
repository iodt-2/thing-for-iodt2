import { Link, useLocation } from "react-router-dom";
import {
  List,
  Plus,
  Search,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { useTranslation } from 'react-i18next';
import useSidebarStore from '@/store/useSidebarStore';

const Sidebar = () => {
  const location = useLocation();
  const { t } = useTranslation();
  const { isCollapsed, toggleCollapse } = useSidebarStore();

  const isActiveLink = (path) => {
    return location.pathname === path
      ? "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border-l-4 border-blue-600"
      : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700";
  };

  // Direct menu items without grouping
  const menuItems = [
    {
      name: t('sidebar.thingList') || 'Thing List',
      path: "/things",
      icon: List
    },
    {
      name: t('sidebar.createThing') || 'Create Thing',
      path: "/things/create",
      icon: Plus
    },
    {
      name: t('sidebar.search') || 'Search',
      path: "/things/search",
      icon: Search
    },
  ];

  return (
    <aside
      className={`fixed left-0 top-16 h-[calc(100vh-4rem)] bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-all duration-300 overflow-hidden ${isCollapsed ? 'w-16' : 'w-64'
        }`}
    >
      {/* Toggle Button */}
      <button
        onClick={toggleCollapse}
        className="absolute -right-3 top-6 z-20 p-2 rounded-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors shadow-md"
        title={isCollapsed ? t('sidebar.expand') || 'Expand' : t('sidebar.collapse') || 'Collapse'}
      >
        {isCollapsed ? (
          <ChevronRight className="h-5 w-5 text-gray-600 dark:text-gray-400" />
        ) : (
          <ChevronLeft className="h-5 w-5 text-gray-600 dark:text-gray-400" />
        )}
      </button>

      {/* Menu Items */}
      <nav className="h-full px-3 pt-20 pb-4 overflow-y-auto">
        <div className="space-y-1">
          {menuItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center space-x-3 px-3 py-3 rounded-lg transition-all ${isActiveLink(item.path)}`}
              title={isCollapsed ? item.name : ''}
            >
              <item.icon className="h-5 w-5 flex-shrink-0" />
              {!isCollapsed && (
                <span className="text-sm font-medium">{item.name}</span>
              )}
            </Link>
          ))}
        </div>
      </nav>
    </aside>
  );
};

export default Sidebar;
