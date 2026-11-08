def get_sidebar_logo():
    """
    Returns HTML markup for displaying a custom logo in the sidebar.
    
    Returns:
        str: HTML string containing a div with an img element for the logo,
             sized at 190x140 pixels.
    """
    return '''
    <div class="sidebar-logo">
        <img src="https://i.postimg.cc/NyJc67wq/oie-DBP9i-CBL61-C8.png" alt="Logo" width="190" height="140">
    </div>
    '''

def get_sidebar_image():
    """
    Returns HTML markup for displaying the Snowflake logo in the sidebar.
    
    Returns:
        str: HTML string containing an img element for the Snowflake logo,
             with responsive width.
    """
    return '''
    <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Snowflake_Logo.svg/1200px-Snowflake_Logo.svg.png" use_column_width=True>
    '''
